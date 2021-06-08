from setuptools import find_packages
from setuptools import setup

setup(name='ctq-sqlalchemy',
      version='1.0.dev1',
      description=open('README.rst').read(),
      long_description=open('README.rst').read(),
      long_description_content_type='text/x-rst',
      classifiers=['Programming Language :: Python', 'Framework :: Pyramid'],
      keywords='traversal context resource',
      author='Olive Link Pty Ltd',
      author_email='software@olivelink.net',
      url='https://github.com/olivelink/ctq',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'ctq',
          'sqlalchemy',
      ])
