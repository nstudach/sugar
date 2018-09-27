from setuptools import setup

setup(name='sugar',
      version='0.1',
      description='Automated Internet Path Transparency Measurements',
      url='http://github.com/nstudach/sugar',
      author='Noah Studach',
      author_email='nstudach@gmail.com',
      license='MIT',
      packages=['sugarpy'],
      install_requires=[
          'requests',
          'pssh.clients',
          'pssh.utils',
          'gevent'
      ],
      zip_safe=False)