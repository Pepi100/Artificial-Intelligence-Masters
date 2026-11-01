package ro.upb.krr.smarthome.model;

/**
 * OWL: Class: LuxSensor SubClassOf: Sensor
 *      DataProperty: measuredLux (Range: xsd:decimal)
 */
public class LuxSensor extends Sensor {
    private double measuredLux;

    public LuxSensor(String id, String locatedIn, double measuredLux) {
        super(id, locatedIn, "on");
        this.measuredLux = measuredLux;
    }

    public double getMeasuredLux()           { return measuredLux; }
    public void setMeasuredLux(double lux)   { this.measuredLux = lux; }

    @Override
    public String toString() {
        return "LuxSensor(" + getId() + " in " + getLocatedIn() + ", lux=" + measuredLux + ")";
    }
}
