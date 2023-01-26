import abc
import re
import shutil
import subprocess
import tempfile
import typing


class Chapter(typing.TypedDict):
    path: str
    title: str | None


class Config(typing.TypedDict):
    author: str
    title: str
    header: str | None
    watermark: str | None
    paragraph_spacing: int
    columns: int
    sources: list[Chapter | None]


class Re:
    # TP - Terminal punctuation
    # NTP - Non-terminal punctuation
    # EOS - End of string
    # SOS - Start of string
    # DQ - Double quote
    # SQ - Single quote

    unicode_double_quotes = re.compile(r'[“”]')
    unicode_single_quotes = re.compile(r'[‘’]')

    nonterminal_punc = ',:;'
    terminal_punc = '.?!'

    multispace = re.compile(r'\s+')

    word_sep = re.compile('|'.join([
        ' ',  # Space
        '(?<=[{0}])(?!\Z|\')'  # After NTP, not before EOS or SQ
    ]).format(nonterminal_punc))

    line_sep = re.compile('|'.join([
        r'(?<=")(?!\Z)',  # After DQ, not before EOS
        r'(?<!\A)(?=")',  # Not after SOS, before DQ
        r'(?<=[^.][{0}]|[{0}]\')'  # After TP not preceded by period, or after TP followed by SQ
        r'(?![{0}_\d\']|\s*"|\Z)'  # Not before a TP, _, or \d, and not before WS preceding DQ, and not before EOS
    ]).format(terminal_punc))

    italic_block = re.compile(r'_([^_]*)_')

    # Whitespace, quote, anything until the first (quote followed by whitespace)
    single_quote_block = re.compile(r'(?s)(?<!\w)\'(.*?)\'(?!\w)')

    double_quote_block = re.compile(r'"\n([^"]*)\n"')

    latex_escape = re.compile(r'([#%&])')


class Text:

    def __init__(self, contents: str):
        self.contents = contents

    def sub(self, old, new) -> typing.Self:
        self.contents = self.contents.replace(old, new)
        return self

    def resub(self, old, new) -> typing.Self:
        self.contents = re.sub(old, new, self.contents)
        return self

    def fix_input(self) -> typing.Self:
        return self.resub(
            Re.multispace, ' '
        ).resub(
            Re.unicode_double_quotes, '"'
        ).resub(
            Re.unicode_single_quotes, "'"
        )


class TxtFormatter:

    def __init__(self, config: Config):
        self.config = config

    @staticmethod
    def split_words(line: str) -> list[str]:
        tokens = [w.strip() for w in re.split(Re.word_sep, line)]
        for i, token in enumerate(tokens[1:], start=1):
            if token in {*Re.nonterminal_punc, *Re.terminal_punc}:
                tokens[i - 1] += token
                tokens[i] = None
        return [t for t in tokens if t is not None]

    @staticmethod
    def split_lines(line: str) -> list[str]:
        return [l.strip() for l in re.split(Re.line_sep, line)]

    @staticmethod
    def take_paragraph(file_) -> typing.Iterator[str]:
        while True:
            line = file_.readline()
            if not line:
                raise EOFError
            line = line.strip()
            if line:
                yield line
                break

        while line := file_.readline().strip():
            yield line

    def take_words(self, words: list[str]) -> tuple[list[str], list[str]]:
        len_ = 0
        i = 0
        for word in words:
            add_len = len(word) + bool(i)
            if len_ + add_len <= self.config['columns']:
                len_ += add_len
                i += 1
            else:
                break
        if i == 0:
            fragment = word[:self.config['columns']:]
            words[0] = word[self.config['columns']:]
            return [fragment], words
        else:
            return words[:i], words[i:]

    def format_paragraph(self, file_) -> typing.Iterator[str]:
        lines = (Text(line).fix_input().contents for line in self.take_paragraph(file_))
        lines = self.split_lines(' '.join(lines))
        for line in lines:
            words = self.split_words(line)
            while words:
                line_fit, words = self.take_words(words)
                yield ' '.join(line_fit)

    def format_file(self, path) -> typing.Iterator[str]:
        with open(path) as f:
            first_paragraph = True
            while True:
                first_line = True
                lines = self.format_paragraph(f)
                while True:
                    try:
                        line = next(lines)
                    except StopIteration:
                        break
                    except EOFError:
                        return
                    else:
                        assert len(line) <= self.config['columns']
                        assert line == line.strip()
                        if first_line and not first_paragraph:
                            yield '\n' * self.config['paragraph_spacing']
                        yield line + '\n'
                        first_line = False
                first_paragraph = False


class Txt2Tex(Text):

    def handle_italics(self) -> typing.Self:
        i = 0
        while (m := Re.italic_block.search(self.contents, i)) is not None:
            before, after = self.contents[:m.start()], self.contents[m.end():]
            content = '\\textit{' + m.group(1).replace('\n\n', '}\n\n\\textit{') + '}'
            i += len(content)
            self.contents = before + content + after
        return self

    def texify(self) -> typing.Self:
        return self.resub(
            Re.latex_escape, r'\\\1'
        ).sub(
            '--', '---'
        ).resub(
            Re.single_quote_block,
            r"`\1'"
        ).resub(
            Re.double_quote_block,
            r"``\1''"
        ).sub(
            # This assumes DQ can nest SQ but not vice-versa,
            # which I think is right because DQ can only occur at top level
            r"'''",
            r"'\thinspace''"
        ).handle_italics()


class GitStatus:

    def run(self, *cmd: str) -> str:
        return subprocess.check_output(cmd).decode()

    def is_git_active(self):
        try:
            return self.run('git', 'status')
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    def get_git_checksum(self) -> str:
        return self.run('git', 'rev-parse', '@').strip()

    def get_git_dirtiness(self) -> bool:
        return bool(self.run('git', 'status', '--porcelain').strip())

    def __str__(self) -> str:
        checksum = self.get_git_checksum()
        if self.get_git_dirtiness():
            return checksum + ' (dirty)'
        else:
            return checksum


class TexCompiler(abc.ABC):

    def cmd(
        self,
        cmd: str,
        params: typing.Iterable[str] = (),
        options: typing.Iterable[str] = (),
    ) -> str:
        options = ','.join(options)
        if options:
            options = f'[{options}]'
        params = ','.join(params)
        return f'\\{cmd}{options}{{{params}}}\n'

    def begin(self, tag) -> str:
        return self.cmd('begin', [tag])

    def end(self, tag) -> str:
        return self.cmd('end', [tag])

    @abc.abstractmethod
    def compile(self) -> typing.Iterator[str]:
        raise NotImplementedError


class TexChapter(TexCompiler):

    def __init__(self, config: Chapter):
        self.config = config

    def compile(self) -> typing.Iterator[str]:
        yield self.cmd('chapter', [] if (title := self.config['title']) is None else [title])
        with open('../' + self.config['path']) as f:
            yield from f


class TexPartBreak(TexCompiler):

    def compile(self) -> typing.Iterator[str]:
        yield self.cmd('part')


class TexDoc(TexCompiler):

    def __init__(self, config: Config):
        self.git_status = GitStatus()
        self.config = config

    def load_chapters(self) -> list[TexChapter | TexPartBreak]:
        chapters = []
        part_found = False
        for source in self.config['sources']:
            if source is None:
                chapters.append(TexPartBreak())
                if chapters and not part_found:
                    chapters.insert(0, TexPartBreak())
                    part_found = True
            else:
                chapters.append(TexChapter(source))
        return chapters

    def compile(self) -> typing.Iterator[str]:

        chapters = self.load_chapters()

        yield self.cmd('documentclass', ['book'])

        yield self.cmd('usepackage', ['indentfirst'])

        if (wm := self.config.get('watermark')) is not None:
            yield self.cmd('usepackage', ['draftwatermark'])
            yield self.cmd('SetWatermarkText', [wm])
            yield self.cmd('SetWatermarkScale', ['0.4'])
            yield self.cmd('SetWatermarkLightness', ['0.875'])

        yield self.cmd('usepackage', ['fontenc'], ['T1'])
        yield self.cmd('usepackage', ['librebaskerville'])

        if (hdr := self.config.get('header')) is not None:
            yield self.cmd('usepackage', ['fancyhdr'])
            yield self.cmd('pagestyle', ['fancy'])
            yield self.cmd('fancyhead', [])
            yield self.cmd('fancyhead',
                           [f'\\textit{hdr}'],
                           ['L'])

        yield self.cmd('setcounter', ['chapter}{-1'])

        yield self.begin('document')

        yield self.cmd('title', [self.config['title']])
        yield self.cmd('author', [self.config['author']])
        yield self.cmd('maketitle')

        if self.git_status.is_git_active():
            yield self.begin('center')
            yield self.cmd('hspace', ['0pt'])
            yield self.cmd('vfill', [])
            yield f'\n{self.git_status}\n'
            yield self.cmd('vfill', [])
            yield self.cmd('hspace', ['0pt'])
            yield self.end('center')

        yield self.cmd('tableofcontents')

        for chapter in chapters:
            yield from chapter.compile()

        yield self.end('document')

def atomic_write(lines: typing.Iterable[str], path) -> None:
    temp = tempfile.mktemp()
    with open(temp, 'x') as f:
        for line in lines:
            f.write(line)
    shutil.move(temp, path)
