Speedwagon Development
======================

Setup Development Environment
-----------------------------
1) Clone/download the speedwagon repository

.. code-block:: shell-session

    developerUser@MYDEVMACHINE ~ % git clone https://github.com/UIUCLibrary/Speedwagon.git
    Cloning into 'Speedwagon'...
    remote: Enumerating objects: 17958, done.
    remote: Counting objects: 100% (1082/1082), done.
    remote: Compressing objects: 100% (489/489), done.
    remote: Total 17958 (delta 820), reused 596 (delta 593), pack-reused 16876 (from 3)
    Receiving objects: 100% (17958/17958), 5.44 MiB | 7.54 MiB/s, done.
    Resolving deltas: 100% (12225/12225), done.

2) Change you current path to the cloned repository and create a virtual environment

.. code-block:: shell-session

    developerUser@MYDEVMACHINE ~ % cd Speedwagon
    developerUser@MYDEVMACHINE Speedwagon % python3 -m venv venv

3) Activate virtual environment

.. code-block:: doscon
    :caption: On **Windows using standard console** (aka cmd.exe) use the activate.bat script:

    c:\Users\developerUser\Speedwagon> venv\Scripts\activate.bat

.. code-block:: pwsh-session
    :caption: On **Windows using Powershell** use the activate.PS1 script:

    PS c:\Users\developerUser\Speedwagon> venv\Scripts\activate.PS1

.. code-block:: shell-session
    :caption: On **Mac or Linux**:

    developerUser@MYDEVMACHINE Speedwagon % source venv/bin/activate

4) Install development dependencies in *requirements-dev.txt*

.. code-block:: shell-session

    (venv) developerUser@MYDEVMACHINE Speedwagon % pip install -r requirements-dev.txt
    Ignoring backports-tarfile: markers 'python_full_version < "3.12"' don't match your environment
    Ignoring exceptiongroup: markers 'python_full_version < "3.11"' don't match your environment
    Ignoring jeepney: markers 'sys_platform == "linux"' don't match your environment
    Ignoring pywin32-ctypes: markers 'sys_platform == "win32"' don't match your environment
    Ignoring secretstorage: markers 'sys_platform == "linux"' don't match your environment
    Ignoring tomli: markers 'python_full_version < "3.11"' don't match your environment
    Collecting alabaster==0.7.16 (from -r requirements-dev.txt (line 3))
      Downloading alabaster-0.7.16-py3-none-any.whl.metadata (2.9 kB)
    Collecting argcomplete==3.5.1 (from -r requirements-dev.txt (line 5))
      Downloading argcomplete-3.5.1-py3-none-any.whl.metadata (16 kB)
    Collecting astroid==3.3.5 (from -r requirements-dev.txt (line 7))
      Downloading astroid-3.3.5-py3-none-any.whl.metadata (4.5 kB)

    ...

    Installing collected packages: wcwidth, snowballstemmer, pyvirtualdisplay, nh3, docopt, distlib, zipp, urllib3, typing-extensions, types-pyyaml, tomlkit, termcolor, sphinxcontrib-serializinghtml, sphinxcontrib-qthelp, sphinxcontrib-jsmath, sphinxcontrib-htmlhelp, sphinxcontrib-devhelp, sphinxcontrib-applehelp, six, shiboken6, ruff, rfc3986, pyyaml, pyqt-distutils, pyproject-hooks, pygments, pyflakes, pydocstyle, pycparser, pycodestyle, propcache, prompt-toolkit, pluggy, platformdirs, pkginfo, packaging, nodeenv, mypy-extensions, multidict, more-itertools, mdurl, mccabe, markupsafe, lxml, jaraco-context, isort, iniconfig, importlib-resources, imagesize, idna, identify, filelock, docutils, dill, decli, coverage, colorama, charset-normalizer, chardet, cfgv, certifi, cachetools, bcrypt, babel, attrs, astroid, argcomplete, alabaster, yarl, virtualenv, types-requests, requests, readme-renderer, questionary, pytest, pyside6-essentials, pyproject-api, pylint, mypy, markdown-it-py, jinja2, jaraco-functools, jaraco-classes, importlib-metadata, flake8, cffi, build, tox, sphinx, rich, requests-toolbelt, pytest-xvfb, pytest-qt, pytest-mock, pyside6-addons, pynacl, pre-commit, keyring, flake8-bugbear, cryptography, commitizen, twine, sphinx-argparse, pyside6, paramiko
    Successfully installed alabaster-0.7.16 argcomplete-3.5.1 astroid-3.3.5 attrs-24.2.0 babel-2.16.0 bcrypt-4.2.1 build-1.2.2.post1 cachetools-5.5.0 certifi-2024.8.30 cffi-1.17.1 cfgv-3.4.0 chardet-5.2.0 charset-normalizer-3.4.0 colorama-0.4.6 commitizen-3.31.0 coverage-7.6.8 cryptography-43.0.3 decli-0.6.2 dill-0.3.9 distlib-0.3.9 docopt-0.6.2 docutils-0.21.2 filelock-3.16.1 flake8-7.1.1 flake8-bugbear-24.10.31 identify-2.6.2 idna-3.10 imagesize-1.4.1 importlib-metadata-8.5.0 importlib-resources-6.4.5 iniconfig-2.0.0 isort-5.13.2 jaraco-classes-3.4.0 jaraco-context-6.0.1 jaraco-functools-4.1.0 jinja2-3.1.4 keyring-25.5.0 lxml-5.3.0 markdown-it-py-3.0.0 markupsafe-3.0.2 mccabe-0.7.0 mdurl-0.1.2 more-itertools-10.5.0 multidict-6.1.0 mypy-1.13.0 mypy-extensions-1.0.0 nh3-0.2.18 nodeenv-1.9.1 packaging-24.2 paramiko-3.5.0 pkginfo-1.10.0 platformdirs-4.3.6 pluggy-1.5.0 pre-commit-4.0.1 prompt-toolkit-3.0.36 propcache-0.2.0 pycodestyle-2.12.1 pycparser-2.22 pydocstyle-6.3.0 pyflakes-3.2.0 pygments-2.18.0 pylint-3.3.1 pynacl-1.5.0 pyproject-api-1.8.0 pyproject-hooks-1.2.0 pyqt-distutils-0.7.3 pyside6-6.8.0.2 pyside6-addons-6.8.0.2 pyside6-essentials-6.8.0.2 pytest-8.3.3 pytest-mock-3.14.0 pytest-qt-4.4.0 pytest-xvfb-3.0.0 pyvirtualdisplay-3.0 pyyaml-6.0.2 questionary-2.0.1 readme-renderer-44.0 requests-2.32.3 requests-toolbelt-1.0.0 rfc3986-2.0.0 rich-13.9.4 ruff-0.8.0 shiboken6-6.8.0.2 six-1.16.0 snowballstemmer-2.2.0 sphinx-7.4.7 sphinx-argparse-0.4.0 sphinxcontrib-applehelp-2.0.0 sphinxcontrib-devhelp-2.0.0 sphinxcontrib-htmlhelp-2.1.0 sphinxcontrib-jsmath-1.0.1 sphinxcontrib-qthelp-2.0.0 sphinxcontrib-serializinghtml-2.0.0 termcolor-2.5.0 tomlkit-0.13.2 tox-4.23.2 twine-5.1.1 types-pyyaml-6.0.12.20240917 types-requests-2.32.0.20241016 typing-extensions-4.12.2 urllib3-2.2.3 virtualenv-20.27.1 wcwidth-0.2.13 yarl-1.18.0 zipp-3.21.0




How to Build Wheel from Source
------------------------------

1) Clone/download the speedwagon repository
2) Install build package (ideally in a virtual environment)
3) Type the following command:
    python -m build

This generates a .whl file which can be installed using pip.


Generate a Release
------------------

Use `commitizen <https://commitizen-tools.github.io/commitizen/>`_ to keep version information consistent.

.. note::
    commitizen is included in requirements-dev.txt

For a beta release use the command ``cz bump --prerelease beta`` with the ``--prerelease-offset=`` flag

.. code-block:: shell-session
    :caption: For example, to release 13th beta of the current working version.

    developerUser@MYDEVMACHINE ~ % cz bump --prerelease beta --prerelease-offset=13
    bump: version 0.4.0.dev13 → 0.4.0b13
    tag to create: 0.4.0b13
    increment detected: MINOR


After releasing a beta, set it back repository to dev and commit this
**BEFORE submitting a pull request**.

.. note::
   There should be no git tag produced for any dev versions. "Dev" versions
   should be considered a "working version".


.. code-block:: console
    :caption: For example, after release 13th beta of the current working version, set the current version to dev 14

    developerUser@MYDEVMACHINE ~ % cz bump --devrelease=14 --no-verify  --files-only
    bump: version 0.4.0b13 → 0.4.0.dev14
    tag to create: 0.4.0.dev14


Make sure you have the "--files-only" flag added or it will create a git tag
for the dev version.  There shouldn't be a git tag for working version
(aka dev version) . However, this command will not commit the files, you will
still have to do that yourself.

.. note::
    If you run into an error such as the following, remove all text from the
    *CHANGELOG.rst* and try again.

    .. code-block:: shell-session

        Traceback (most recent call last):
          File "/Users/developerUser/PycharmProjects/UIUCLibrary/Speedwagon/venv/bin/cz", line 8, in <module>
            sys.exit(main())
                     ^^^^^^
          File "/Users/developerUser/PycharmProjects/UIUCLibrary/Speedwagon/venv/lib/python3.11/site-packages/commitizen/cli.py", line 656, in main
            args.func(conf, arguments)()
          File "/Users/developerUser/PycharmProjects/UIUCLibrary/Speedwagon/venv/lib/python3.11/site-packages/commitizen/commands/bump.py", line 338, in __call__
            changelog_cmd()
          File "/Users/developerUser/PycharmProjects/UIUCLibrary/Speedwagon/venv/lib/python3.11/site-packages/commitizen/commands/changelog.py", line 177, in __call__
            changelog_meta = self.changelog_format.get_metadata(self.file_name)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          File "/Users/developerUser/PycharmProjects/UIUCLibrary/Speedwagon/venv/lib/python3.11/site-packages/commitizen/changelog_formats/base.py", line 46, in get_metadata
            return self.get_metadata_from_file(changelog_file)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          File "/Users/developerUser/PycharmProjects/UIUCLibrary/Speedwagon/venv/lib/python3.11/site-packages/commitizen/changelog_formats/restructuredtext.py", line 55, in get_metadata_from_file
            kind = second[0]
                   ~~~~~~^^^
