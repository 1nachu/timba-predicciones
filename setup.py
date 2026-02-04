from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        "src.timba_fast",
        ["src/timba_fast.pyx"],
    )
]

setup(
    name="Timba Fast Engine",
    ext_modules=cythonize(extensions, compiler_directives={'language_level': "3"}),
)
