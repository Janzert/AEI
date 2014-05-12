
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'readme.txt')).read()

setup(name='AEI',
      version='1.2.dev',
      description='Arimaa Engine Interface tools',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
          ],
      author='Janzert',
      author_email='janzert@janzert.com',
      url='http://arimaa.janzert.com/aei',
      keywords='arimaa',
      packages=find_packages(exclude=["tests"]),
      )
