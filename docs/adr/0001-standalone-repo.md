# Standalone repo, not an OpenSTEF fork

The narrator lives in its own repository rather than as a fork or subpackage of OpenSTEF. OpenSTEF is maintained by Alliander with its own release cycle; coupling the narrator to it would mean tracking their releases, matching their Python version requirements, and navigating their PR process before we can ship. A standalone package that works with mock data (for the showcase) and accepts OpenSTEF DataFrames via an adapter (for production) gives us independence without losing integration.
