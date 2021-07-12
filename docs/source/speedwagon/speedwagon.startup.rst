speedwagon.startup
==================

.. automodule:: speedwagon.startup

Configuring how Speedwagon starts
---------------------------------

ApplicationLauncher is needed to start speedwagon.

.. autoclass:: speedwagon.startup.ApplicationLauncher

To change how it starts change the strategy with an AbsStarter class.

Starters
________

.. autoclass:: speedwagon.startup.StartupDefault

.. autoclass:: speedwagon.startup.SingleWorkflowLauncher
