About Speedwagon
================

Collection of tools and workflows for DS


`Documentation <https://www.library.illinois.edu/dccdocs/speedwagon/>`_

`Download <https://nexus.library.illinois.edu/service/rest/repository/browse/prescon-dist/speedwagon/>`_

.. admonition:: Development Status

    .. container::

        .. image:: https://img.shields.io/badge/License-UIUC%20License-green.svg?label=License
           :target: https://otm.illinois.edu/disclose-protect/illinois-open-source-license

        .. image:: https://jenkins-prod.library.illinois.edu/buildStatus/icon?job=open+source%2Fspeedwagon%2Fmaster
           :target: https://jenkins-prod.library.illinois.edu/job/open%20source/job/speedwagon/job/master/

        .. image:: https://img.shields.io/jenkins/coverage/api/https://jenkins-prod.library.illinois.edu/job/open%20source/job/speedwagon/job/master/coverage/   
           :alt: Jenkins Coverage
           :target: https://jenkins-prod.library.illinois.edu/job/open%20source/job/speedwagon/job/master/coverage/
           
How to Build Wheel from Source
------------------------------

1) Clone/download this repository
2) Install build package (ideally in a virtual environment)
3) Type the following command:
    python -m build

This generates a .whl file which can be installed using pip.
