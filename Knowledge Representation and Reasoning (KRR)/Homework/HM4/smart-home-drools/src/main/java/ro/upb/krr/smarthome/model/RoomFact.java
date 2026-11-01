package ro.upb.krr.smarthome.model;

import java.util.Objects;

/**
 * Base class for facts DERIVED by rules about a room (OccupiedRoom, DarkRoom, EmptyRoom).
 *
 * In OWL these are classes an individual is inferred to belong to, e.g. OccupiedRoom(livingRoom).
 * In Drools they are separate fact objects inserted with insertLogical(...).
 *
 * equals/hashCode are REQUIRED: the truth-maintenance system recognises two logical
 * insertions of "the same" fact by equality and merges their justifications.
 */
public abstract class RoomFact {
    private final String room;

    protected RoomFact(String room) { this.room = room; }

    public String getRoom() { return room; }

    @Override
    public boolean equals(Object o) {
        return o != null && o.getClass() == getClass() && Objects.equals(room, ((RoomFact) o).room);
    }

    @Override
    public int hashCode() { return Objects.hash(getClass().getName(), room); }

    @Override
    public String toString() { return getClass().getSimpleName() + "(" + room + ")"; }
}
