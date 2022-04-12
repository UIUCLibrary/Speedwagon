About Speedwagon
================

Collection of tools and workflows for DS


`Documentation <https://www.library.illinois.edu/dccdocs/speedwagon/>`_

`Download <https://jenkins.library.illinois.edu/nexus/service/rest/repository/browse/prescon-dist/speedwagon/>`_

.. admonition:: Development Status

    .. container::

        .. image:: https://img.shields.io/badge/License-UIUC%20License-green.svg?label=License
           :target: https://otm.illinois.edu/disclose-protect/illinois-open-source-license

        .. image:: https://jenkins.library.illinois.edu/buildStatus/icon?job=OpenSourceProjects/Speedwagon/master
           :target: https://jenkins.library.illinois.edu/job/OpenSourceProjects/job/Speedwagon/job/master/

        .. image:: https://img.shields.io/jenkins/coverage/api/https/jenkins.library.illinois.edu/job/OpenSourceProjects/job/Speedwagon/job/master   
           :alt: Jenkins Coverage
           :target: https://jenkins.library.illinois.edu/job/OpenSourceProjects/job/Speedwagon/job/master/coverage/
           
How to Build Wheel from Source
------------------------------

1) Clone/download this repository
2) Install build package (ideally in a virtual environment)
3) Type the following command:
    python -m build

This generates a .whl file which can be installed using pip.
