package ro.upb.krr.smarthome.model;

/**
 * OWL: Class: Room
 *      DataProperty: hasState          (e.g. "normal", "quiet")
 *      DataProperty: lastMotionMinutes (xsd:integer)
 */
public class Room {
    private final String id;
    private String hasState;
    private int lastMotionMinutes;

    public Room(String id, String hasState, int lastMotionMinutes) {
        this.id = id;
        this.hasState = hasState;
        this.lastMotionMinutes = lastMotionMinutes;
    }

    public String getId()                       { return id; }
    public String getHasState()                 { return hasState; }
    public void setHasState(String s)           { this.hasState = s; }
    public int getLastMotionMinutes()           { return lastMotionMinutes; }
    public void setLastMotionMinutes(int m)     { this.lastMotionMinutes = m; }

    @Override
    public String toString() {
        return "Room(" + id + ", state=" + hasState + ", lastMotion=" + lastMotionMinutes + "min)";
    }
}
