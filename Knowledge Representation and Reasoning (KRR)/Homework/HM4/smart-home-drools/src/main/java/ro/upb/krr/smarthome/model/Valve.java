package ro.upb.krr.smarthome.model;

/** OWL: Class: Valve SubClassOf: Device  (state "open" / "closed") - used in the exercises */
public class Valve extends Device {
    public Valve(String id, String locatedIn, String hasState) {
        super(id, locatedIn, hasState);
    }
}
