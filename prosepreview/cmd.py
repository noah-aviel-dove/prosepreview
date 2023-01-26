import abc
import argparse
import json
import os
import pathlib
import shutil

import prosepreview


class Action(abc.ABC):
    package_root = pathlib.Path(__file__).resolve().parent
    package_name = package_root.name
    cwd = pathlib.Path.cwd()

    def __init__(self, name: str | None):
        self.name = name
        self.parser = argparse.ArgumentParser(prog=self.prog, add_help=False)

    @property
    def prog(self):
        parts = (
            self.package_name,
            *(() if self.name is None else (self.name,)),
        )
        return ' '.join(parts)

    def load_config(self) -> prosepreview.Config:
        try:
            with open(self.cwd / 'config.json') as f:
                config = json.load(f)
        except FileNotFoundError:
            raise
        else:
            return config

    @abc.abstractmethod
    def __call__(self, argv):
        return self.parser.parse_args(argv)


class Init(Action):

    def __init__(self):
        super().__init__('init')
        self.parser.add_argument('dir', nargs='?', default=self.package_name)

    def __call__(self, argv):
        args = super().__call__(argv)
        target = self.cwd / args.dir
        shutil.copytree(self.package_root / 'template', target)
        os.makedirs(target / '.format')
        os.makedirs(target / '.tex')


class Format(Action):

    def __init__(self):
        super().__init__('format')
        self.parser.add_argument('txt_file', type=pathlib.Path)

    def __call__(self, argv):
        args = super().__call__(argv)
        formatter = prosepreview.TxtFormatter(self.load_config())
        lines = formatter.format_file(args.txt_file)
        prosepreview.atomic_write(lines, args.txt_file)


class Texify(Action):

    def __init__(self):
        super().__init__('texify')
        self.parser.add_argument('txt_file', type=pathlib.Path)
        self.parser.add_argument('tex_file', type=pathlib.Path)

    def __call__(self, argv):
        args = super().__call__(argv)
        with open(args.txt_file) as f:
            text = f.read()
        text = prosepreview.Txt2Tex(text).texify().contents
        with open(args.tex_file, 'w') as f:
            f.write(text)


class Compile(Action):

    def __init__(self):
        super().__init__('compile')
        self.parser.add_argument('tex_file', type=pathlib.Path)

    def __call__(self, argv):
        args = super().__call__(argv)
        tex = prosepreview.TexDoc(self.load_config())
        lines = tex.compile()
        prosepreview.atomic_write(lines, args.tex_file)


class Root(Action):
    actions = {
        'init': Init(),
        'format': Format(),
        'texify': Texify(),
        'compile': Compile()
    }

    def __init__(self):
        super().__init__(None)
        self.parser.add_argument('action', choices=list(self.actions))

    def __call__(self, argv):
        args = super().__call__(argv[:1])
        self.actions[args.action](argv[1:])
