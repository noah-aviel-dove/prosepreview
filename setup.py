import setuptools

setuptools.setup(
    name='prosepreview',
    version='0.9.0',
    description='VCS-compatible formatting and LaTeX conversion for natural-language writing projects',
    url='https://github.com/noah-aviel-dove/prosepreview',
    author_email='noah.aviel.dove@gmail.com',
    license='GPLv3',
    packages=['prosepreview'],
    package_data={
        'prosepreview': [
            'template/config.json',
            'template/Makefile'
        ]
    },
    python_requires='>=3.11.1',
)
