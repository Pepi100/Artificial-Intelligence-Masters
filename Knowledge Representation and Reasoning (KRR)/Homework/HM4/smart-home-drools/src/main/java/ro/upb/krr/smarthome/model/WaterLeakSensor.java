package ro.upb.krr.smarthome.model;

/** OWL: Class: WaterLeakSensor SubClassOf: Sensor  (state "wet" / "dry") - used in the exercises */
public class WaterLeakSensor extends Sensor {
    public WaterLeakSensor(String id, String locatedIn, String hasState) {
        super(id, locatedIn, hasState);
    }
}
