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

2) Change you current path to the cloned repository and create a development environment with uv

.. code-block:: shell-session

    developerUser@MYDEVMACHINE ~ % cd Speedwagon
    developerUser@MYDEVMACHINE Speedwagon % uv sync

3) Activate virtual environment

.. code-block:: doscon
    :caption: On **Windows using standard console** (aka cmd.exe) use the activate.bat script:

    c:\Users\developerUser\Speedwagon> .venv\Scripts\activate.bat

.. code-block:: pwsh-session
    :caption: On **Windows using Powershell** use the activate.PS1 script:

    PS c:\Users\developerUser\Speedwagon> .venv\Scripts\activate.PS1

.. code-block:: shell-session
    :caption: On **Mac or Linux**:

    developerUser@MYDEVMACHINE Speedwagon % source .venv/bin/activate



How to Build Wheel from Source
------------------------------

.. note::

    This method requires uv to be installed.


1) Clone/download the speedwagon repository
2) Type the following command:
    uv build

This generates a .whl file which can be installed using pip or uv.


Generate a Release
------------------

Use `commitizen <https://commitizen-tools.github.io/commitizen/>`_ to keep version information consistent.

.. note::
    commitizen is not included in the development environment, so you will need to install it separately. You can do
    this with pip, uv or another package manager.

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
