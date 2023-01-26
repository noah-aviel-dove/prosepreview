SHELL=/bin/bash

py=python3.11
package_name=prosepreview
source_dir=..
tex_dir=.tex
format_dir=.format
config_file=config.json
output_file=preview
source_files=$(shell cat ${config_file} | jq .sources[].path | jq -r)
format_tags=$(patsubst %.txt,${format_dir}/%.format,${source_files})
tex_files=$(patsubst %.txt,${tex_dir}/%.tex,${source_files})
columns=$(shell cat ${config_file} | jq .columns)


.PHONY: compile
compile: ${output_file}.pdf


.PHONY: format
format: ${format_tags}


.PHONY: clean
clean:
	rm -f ${output_file}.pdf ${format_dir}/* ${tex_dir}/*


${output_file}.pdf: ${tex_dir}/${output_file}.tex
	pdflatex -output-directory=${tex_dir} -halt-on-error $<
	mv ${tex_dir}/$@ $@


${tex_dir}/${output_file}.tex: ${tex_files}
	${py} -m ${package_name} compile $@


${tex_dir}/%.tex: ${source_dir}/%.txt ${format_dir}/%.format
	${py} -m ${package_name} texify $< $@


${format_dir}/%.format: ${source_dir}/%.txt
	${py} -m ${package_name} format $<
	touch $@


${source_dir}/%.txt: ${source_dir}/%.docx
	pandoc --from=docx --to=asciidoc --columns ${columns} $< -o $@
