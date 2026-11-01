package ro.upb.krr.smarthome.model;

import java.util.Objects;

/**
 * Base class for the "intent" markers DERIVED by rules about a device
 * (DesiredOn, DesiredOff, DesiredClose, SuppressedAction).
 * Same equality contract as RoomFact.
 */
public abstract class DeviceFact {
    private final String device;

    protected DeviceFact(String device) { this.device = device; }

    public String getDevice() { return device; }

    @Override
    public boolean equals(Object o) {
        return o != null && o.getClass() == getClass() && Objects.equals(device, ((DeviceFact) o).device);
    }

    @Override
    public int hashCode() { return Objects.hash(getClass().getName(), device); }

    @Override
    public String toString() { return getClass().getSimpleName() + "(" + device + ")"; }
}
