package ro.upb.krr.smarthome.model;

/**
 * Marks a room for which contradictory facts were derived
 * (OWL equivalent: DisjointClasses: OccupiedRoom, EmptyRoom -> the reasoner reports an inconsistency).
 */
public class Inconsistency extends RoomFact {
    public Inconsistency(String room) { super(room); }
}
