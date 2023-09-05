from setuptools import setup, find_packages
import os

def read_requirements():
    with open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), 'r') as file:
        return [line.strip() for line in file if not line.startswith('#')]

setup(
    name='mafiascum_modtools',
    version='0.1.0',
    description='moderator tools for mafiascum',
    author='fbastos1',
    author_email='felipe.v.b@icloud.com',
    packages=['mafiascum_modtools'],
    install_requires=read_requirements(),
    entry_points={
        'console_scripts': [
            'votecounter = mafiascum_modtools.votecounter:main',  # Replace 'main' with the name of your main function
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
