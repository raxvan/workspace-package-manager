from setuptools import setup, find_packages

setup(
    name = "workspace-package-manager",
    version = "0.0.1",
    description = "This is a package manager designed for developers.",
    long_description = open('README.md').read(),
    long_description_content_type = 'text/markdown',
    packages = find_packages(),
    install_requires = [
        "GitPython",
        "requests"
    ],
    python_requires = '>=3.6',
    entry_points = {
        'console_scripts': [
            'wpm=wpmcli.cli:main',
        ],
    }
)