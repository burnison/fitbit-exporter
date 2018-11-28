from setuptools import setup, find_packages

setup(
        name='fitbit-exporter',
        version='1.0.0',
        description='Fitbit Exporter',

        author='Richard Burnison',
        author_email='richard@burnison.ca',
        url='https://github.com/burnison/fitbit-exporter',

        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,

        install_requires=[
            'oauth2client>=4.1.0',
            'graphitesend>=0.10.0',
            'pytz>=2018.3',
        ],

        entry_points={
            'console_scripts':['fitbit-exporter = fitbit.exporter:main']
        }
)
