
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'readme.rst')).read()

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
      entry_points="""\
      [console_scripts]
      analyze = pyrimaa.analyze:main
      gameroom = pyrimaa.gameroom:main
      postal_controller = pyrimaa.postal_controller:main
      pyrimaa_tests = pyrimaa.test_runner:main
      roundrobin = pyrimaa.roundrobin:main
      simple_engine = pyrimaa.simple_engine:main
      """,
      )
