# Experimental USB transaction cancellation

The opt-in GUI now creates a private temporary cancellation marker and passes its path to the experimental writer. Clicking Cancel creates the marker. The backend polls it before authorization, during writing and during SHA-256 readback. The GUI does not terminate the process or close the authorized descriptor forcibly.

**Warning:** cancellation after the first write leaves a partially overwritten USB device; do not unplug it until the writer exits. This is still experimental and is not a release candidate. Hardware/Polkit tests and Qt6 compilation have not been performed in this environment.
