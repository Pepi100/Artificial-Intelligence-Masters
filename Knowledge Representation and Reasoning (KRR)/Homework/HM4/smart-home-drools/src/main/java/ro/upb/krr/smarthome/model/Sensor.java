package ro.upb.krr.smarthome.model;

/** OWL: Class: Sensor SubClassOf: Device */
public abstract class Sensor extends Device {
    protected Sensor(String id, String locatedIn, String hasState) {
        super(id, locatedIn, hasState);
    }
}
