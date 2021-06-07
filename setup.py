import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'readme.rst')).read()

setup(name='AEI',
      version='1.3.0',
      description='Arimaa Engine Interface tools',
      long_description=README,
      long_description_content_type='text/x-rst',
      classifiers=["Programming Language :: Python",
                   "Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 3",
                   "Intended Audience :: Developers",
                   "Topic :: Games/Entertainment :: Board Games", ],
      author='Janzert',
      author_email='janzert@janzert.com',
      url='https://arimaa.janzert.com/aei',
      project_urls={
          'Source Code': 'https://github.com/janzert/aei',
      },
      keywords='Arimaa',
      python_requires='>=2.7',
      packages=find_packages(),
      entry_points="""\
      [console_scripts]
      analyze = pyrimaa.analyze:main
      gameroom = pyrimaa.gameroom:main
      postal_controller = pyrimaa.postal_controller:main
      pyrimaa_tests = pyrimaa.test_runner:main
      roundrobin = pyrimaa.roundrobin:main
      simple_engine = pyrimaa.simple_engine:main
      """, )
