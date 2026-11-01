package ro.upb.krr.smarthome.model;

/**
 * OWL:  Class: Device
 *       ObjectProperty: locatedIn  (Range: Room)
 *       DataProperty:   hasState   (Range: xsd:string)
 *
 * In Drools the OWL class hierarchy becomes a Java class hierarchy:
 * a pattern Device(...) also matches every subclass (Light, MotionSensor, ...).
 */
public abstract class Device {
    private final String id;
    private final String locatedIn;   // id of the Room
    private String hasState;          // "on", "off", ...

    protected Device(String id, String locatedIn, String hasState) {
        this.id = id;
        this.locatedIn = locatedIn;
        this.hasState = hasState;
    }

    public String getId()                { return id; }
    public String getLocatedIn()         { return locatedIn; }
    public String getHasState()          { return hasState; }
    public void setHasState(String s)    { this.hasState = s; }

    @Override
    public String toString() {
        return getClass().getSimpleName() + "(" + id + " in " + locatedIn + ", state=" + hasState + ")";
    }
}
