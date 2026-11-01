package ro.upb.krr.smarthome;

import java.util.Comparator;
import java.util.List;

import org.kie.api.KieServices;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;

import ro.upb.krr.smarthome.model.*;

/**
 * KRR Lab 4 - runs the smart-home rule base through a short scenario.
 *
 * The working memory (WM) holds the Home Assistant entities as facts.
 * After each change we call fireAllRules() and print what was derived.
 *
 * The rule base comes in two versions (see META-INF/kmodule.xml), chosen by the
 * first command-line argument:
 *   salience - rules/salience/*.drl, inference before actuation via salience (default)
 *   agenda   - rules/agenda/*.drl,   inference before actuation via agenda groups
 */
public class SmartHomeApp {

    private final KieSession session;
    private final boolean agendaGroups;

    // --- the house (one object per Home Assistant entity, as on slide 27) ---
    private final Room livingRoom = new Room("livingRoom", "normal", 0);
    private final MotionSensor motion1 = new MotionSensor("motion1", "livingRoom", "on");
    private final LuxSensor lux1 = new LuxSensor("lux1", "livingRoom", 12);
    private final Light lamp1 = new Light("lamp1", "livingRoom", "off");

    private final Room bedroom = new Room("bedroom", "quiet", 0);
    private final MotionSensor motion2 = new MotionSensor("motion2", "bedroom", "on");
    private final LuxSensor lux2 = new LuxSensor("lux2", "bedroom", 5);
    private final Light lamp2 = new Light("lamp2", "bedroom", "off");

    private final Room kitchen = new Room("kitchen", "normal", 45);
    private final MotionSensor motion3 = new MotionSensor("motion3", "kitchen", "off");
    private final LuxSensor lux3 = new LuxSensor("lux3", "kitchen", 300);
    private final Light lamp3 = new Light("lamp3", "kitchen", "on");


    //bathroom
    private final Room bathroom = new Room("bathroom", "normal", 0);
    private final WaterLeakSensor leak1 = new WaterLeakSensor("leak1", "bathroom", "dry");
    private final Valve valve1 = new Valve("valve1", "bathroom", "open");


    public SmartHomeApp(String version) {
        if (!version.equals("salience") && !version.equals("agenda")) {
            throw new IllegalArgumentException("Unknown version '" + version + "': use 'salience' or 'agenda'");
        }
        agendaGroups = version.equals("agenda");
        KieServices ks = KieServices.Factory.get();
        KieContainer container = ks.getKieClasspathContainer();
        // the ksession names are declared in kmodule.xml: salienceSession, agendaSession
        session = container.newKieSession(version + "Session");
    }

    public static void main(String[] args) {
        String version = args.length > 0 ? args[0] : "salience";
        System.out.println("Rule base version: " + version);
        SmartHomeApp app = new SmartHomeApp(version);
        try {
            app.run();
        } finally {
            app.session.dispose();
        }
    }

    private void run() {
        step("0. Initial state: insert all entities", () -> {
            for (Object o : List.of(livingRoom, motion1, lux1, lamp1,
                                    bedroom, motion2, lux2, lamp2,
                                    kitchen, motion3, lux3, lamp3,
                                    bathroom, leak1, valve1)) {
                session.insert(o);
            }
        });

        step("1. Motion stops in the living room (motion1 -> off)", () -> {
            motion1.setHasState("off");
            update(motion1);
        });

        step("2. 40 minutes pass without motion in the living room", () -> {
            livingRoom.setLastMotionMinutes(40);
            update(livingRoom);
        });

        step("3. Stale data: motion1 reports 'on' again, but lastMotionMinutes is still 40", () -> {
            motion1.setHasState("on");
            update(motion1);
        });

        step("4. Home Assistant refreshes the timestamp (lastMotionMinutes -> 0)", () -> {
            livingRoom.setLastMotionMinutes(0);
            update(livingRoom);
        });

        step("5. Night mode ends in the bedroom (bedroom state 'quiet' -> 'normal')", () -> {
            bedroom.setHasState("normal");
            update(bedroom);

            
        });

        step("6. Water leak detected in the bathroom", () -> {
            leak1.setHasState("wet");
            update(leak1);
        });
    }

    // ------------------------------------------------------------------ helpers

    /** Tell the engine that a fact changed (like modify(...) in a rule RHS). */
    private void update(Object fact) {
        session.update(session.getFactHandle(fact), fact);
    }

    private void step(String title, Runnable change) {
        System.out.println();
        System.out.println("=== " + title);
        change.run();
        int fired = agendaGroups ? fireWithAgendaGroups() : session.fireAllRules();
        System.out.println("  (" + fired + " rule firings)");
        printState();
    }

    /**
     * Agenda-group version. The focus is a stack: the last group focused runs first,
     * so "inference" runs to completion, then "actuation" gets the focus.
     * An actuation can make an inference rule stop matching; Drools only
     * re-evaluates that rule (and retracts its logical conclusion) when
     * "inference" has the focus again - hence the loop.
     */


    // private int fireWithAgendaGroups() {
    //     session.getAgenda().getAgendaGroup("actuation").setFocus();
    //     session.getAgenda().getAgendaGroup("inference").setFocus();

    //     return session.fireAllRules();
    // }
    private int fireWithAgendaGroups() {
        int fired = 0, n;
        do {
            session.getAgenda().getAgendaGroup("actuation").setFocus();
            session.getAgenda().getAgendaGroup("inference").setFocus();
            n = session.fireAllRules();
            fired += n;
        } while (n > 0);
        return fired;
    }

    private void printState() {
        List<String> derived = session.getObjects(o -> o instanceof RoomFact || o instanceof DeviceFact)
                .stream().map(Object::toString).sorted().toList();
        List<String> lights = session.getObjects(o -> o instanceof Light)
                .stream().map(o -> (Light) o)
                .sorted(Comparator.comparing(Light::getId))
                .map(l -> l.getId() + "=" + l.getHasState()).toList();
        System.out.println("  Derived facts: " + (derived.isEmpty() ? "(none)" : String.join(", ", derived)));
        System.out.println("  Lights       : " + String.join(", ", lights));
    }
}
