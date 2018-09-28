from setuptools import setup

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(name = 'sugar',
      version = '0.1',
      description = 'Automated Internet Path Transparency Measurements',
      url = 'http://github.com/nstudach/sugar',
      author = 'Noah Studach',
      author_email = 'nstudach@gmail.com',
      license = 'GNU GPLv2',
      classifiers = [
        # The UI
        'Environment :: Console',

        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',
        'Topic :: Communications',
        'Topic :: Internet',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',

        # Specify the Python versions you support here
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
      ],
      packages = ['sugarpy'],
      install_requires = install_requires,
      entry_points = {
        'console_scripts': [
            'sugar=sugarpy.main:comand_line_parser',
        ],
      },
      zip_safe = False)