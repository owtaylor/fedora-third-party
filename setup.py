from setuptools import setup

entry_points = '''
    [console_scripts]
    fedora-third-party=fedora_third_party.cli:cli
'''

setup(name='fedora-third-party',
      version='0.1',
      description='Tool for managing third-party repositories on Fedora',
      url='https://pagure.io/fedora-third-party',
      author='Owen Taylor',
      author_email='otaylor@redhat.com',
      license='MIT',
      packages=['fedora_third_party', 'tests'],
      include_package_data=True,
      entry_points=entry_points,
      )
