# KRR Lab 4 — Smart home rules in Drools

In Lecture 3 (slides 25–34) we wrote smart-home automation rules in **SWRL** over a small
OWL ontology (rooms, sensors, lights). Slide 33 listed what SWRL cannot do because it is
**monotonic**: it never retracts a conclusion and has no negation as failure.

In this lab you run the **same rules in Drools**, a production-rule engine, and see how it
handles those problems.

---

## 1. Set up the environment (≈ 15 min, do this once)

### 1.1 Install
| What | Version | Where |
|---|---|---|
| **JDK** | 21 | <https://adoptium.net> (Temurin). Tick *"Set JAVA_HOME"* in the installer. |
| **VS Code** | latest | <https://code.visualstudio.com> |
| **Extension Pack for Java** (Microsoft) | latest | VS Code → Extensions (`Ctrl+Shift+X`) → search *Extension Pack for Java*. It includes Maven support. |
| *(optional)* a DRL syntax highlighter | – | Extensions → search *Drools* and install one that highlights `.drl` files. |

You do **not** need to install Maven separately: the Java extension pack bundles it, and VS Code
downloads Drools automatically the first time the project is opened (internet access required).
If you want to use the terminal commands in section 1.4, install Maven from
<https://maven.apache.org/download.cgi> as well.

Check the JDK in a terminal:
```
java -version      # must print 21
```

### 1.2 Open the project
1. Unzip `smart-home-drools.zip`.
2. VS Code → **File → Open Folder…** → select the `smart-home-drools` folder (the one containing `pom.xml`).
3. Accept *"Do you trust the authors?"* and, if prompted, install the recommended extensions.
4. Wait until the status bar shows **Java: Ready** (first time: 1–3 minutes while Maven downloads Drools).

### 1.3 Run it
The rule base comes in two versions that differ only in how they make inference run before
actuation (see section 2.1): **salience** (the default) and **agenda groups**.

Open the *Run and Debug* view (`Ctrl+Shift+D`), pick *Run SmartHomeApp (salience)* or
*Run SmartHomeApp (agenda groups)* from `.vscode/launch.json`, and press **F5**.
Clicking **Run** above `main` runs the salience version.

### 1.4 Run from the terminal (alternative)
```
mvn compile exec:java                          # salience version
mvn compile exec:java -Dexec.args=agenda       # agenda-group version
```

### Troubleshooting
| Symptom | Fix |
|---|---|
| `Java: Ready` never appears / red errors on `org.kie...` imports | `Ctrl+Shift+P` → **Java: Clean Java Language Server Workspace** → Restart. |
| `JAVA_HOME is not set` or wrong version | Set `JAVA_HOME` to the JDK 21 folder, or `Ctrl+Shift+P` → **Java: Configure Java Runtime**. |
| `Cannot find KieSession salienceSession` / `No kmodule.xml` | The file must be at `src/main/resources/META-INF/kmodule.xml`. Rebuild. |
| A rule you added never fires | Check that its file is in a folder listed in `packages="..."` in `kmodule.xml`, and that its `package` line matches the folder. |
| Rule errors at startup (`Unable to resolve ObjectType`, `[ERR 102]`) | A syntax error in a `.drl` file — the message gives the file and line. |
| Download fails behind the faculty proxy | Configure Maven's proxy in `~/.m2/settings.xml`. |

---

## 2. Project structure

```
smart-home-drools/
├── pom.xml                                 Maven build: Drools dependencies
├── src/main/java/ro/upb/krr/smarthome/
│   ├── SmartHomeApp.java                   the house + a 6-step scenario
│   └── model/                              the ontology as Java classes
│       ├── Device, Sensor, MotionSensor, LuxSensor, WaterLeakSensor, Light, Valve, Room
│       ├── OccupiedRoom, DarkRoom, EmptyRoom          derived room classes
│       ├── DesiredOn, DesiredOff, DesiredClose, SuppressedAction   intent markers
│       └── Inconsistency                               new: conflict marker
└── src/main/resources/
    ├── META-INF/kmodule.xml                which rule files form each knowledge base
    └── ro/upb/krr/smarthome/rules/
        ├── salience/                       version 1: ordering by salience
        │   ├── 01-inference.drl            R1–R6: the SWRL rules, translated
        │   ├── 02-consistency.drl          C1: OccupiedRoom / EmptyRoom disjointness
        │   └── 03-actuation.drl            A1–A4: act on the intents (what HA did on slide 32)
        └── agenda/                         version 2: same rules, ordering by agenda groups
            ├── 01-inference.drl
            ├── 02-consistency.drl
            └── 03-actuation.drl
```

The two folders contain the **same rules**; only the attributes that order them differ.
Unless an exercise says otherwise, work in `rules/salience/`.

### 2.1 Choosing which rule files run: `kmodule.xml`
Drools does not load every `.drl` file it finds. `kmodule.xml` declares **knowledge bases**
(`kbase`), and each one lists the rule **packages** it contains. A package is a folder under
`src/main/resources`, and the `package` line at the top of each `.drl` file must match it:

```xml
<kbase name="salienceKB" packages="ro.upb.krr.smarthome.rules.salience">
  <ksession name="salienceSession" type="stateful" default="true"/>
</kbase>
<kbase name="agendaKB" packages="ro.upb.krr.smarthome.rules.agenda">
  <ksession name="agendaSession" type="stateful"/>
</kbase>
```

`SmartHomeApp` opens a session by name, `container.newKieSession("salienceSession")`, and
gets exactly the rules of that knowledge base. To run a different set of rule files, put them
in their own folder (= package) and list it in `packages`. Several packages are separated by
commas: `packages="a.b.c, a.b.d"`. A `kbase` can also reuse another one with
`includes="otherKB"`.

### 2.2 Inference before actuation: salience vs. agenda groups
Rules A1–A4 *act* on what R1–R6 and C1 *derive*, so they must wait until derivation is
complete. Otherwise, for example, A1 could turn on a lamp before R4 has derived that it is
suppressed. The two versions enforce this in different ways:

| | `rules/salience/` | `rules/agenda/` |
|---|---|---|
| Inference rules (R1–R6, C1) | default `salience 0` | `agenda-group "inference"` + `auto-focus true` |
| Actuation rules (A1–A4) | `salience -10` | `agenda-group "actuation"` |
| Java side | just `fireAllRules()` | set the focus (`"actuation"`, then `"inference"` on top), then `fireAllRules()` in a loop |

- **Salience** is a priority *inside one agenda*: whenever both an inference and an
  actuation rule can fire, the one with the higher salience fires first.
- **Agenda groups** split the rules into separate agendas. Only the group that has the
  **focus** fires. The focus is a stack: `SmartHomeApp` pushes `"actuation"` and then
  `"inference"`, so inference runs to completion, is popped, and actuation takes over.
- **`auto-focus true`**: an actuation can change a fact so that an inference rule matches
  again (e.g. A1 turns a light on and R6 looks for lights that are on). `auto-focus` makes
  the inference group take the focus back as soon as one of its rules gets a new match.
- **Why the loop?** `auto-focus` only reacts to *new* matches. If an actuation makes an
  inference rule *stop* matching, Drools re-evaluates that rule (and retracts its
  `insertLogical` conclusion) only when `"inference"` has the focus again. Without the
  loop, a stale `DesiredOff(lamp1)` stays in working memory after step 2.

### From OWL to Java
| OWL (slides 28–29) | Drools / Java |
|---|---|
| `Class: Light SubClassOf: Device` | `class Light extends Device` — a pattern `Device(...)` also matches lights |
| `Individual: lamp1` | a Java object inserted into working memory: `new Light("lamp1", "livingRoom", "off")` |
| `ObjectProperty: locatedIn` | field `locatedIn` (holds the room id) |
| `DataProperty: hasState`, `measuredLux`, `lastMotionMinutes` | fields with the same names |
| derived class `OccupiedRoom(?r)` | a separate fact `new OccupiedRoom("livingRoom")` |

### From SWRL to DRL
| SWRL | DRL |
|---|---|
| `MotionSensor(?s)` | `MotionSensor( ... )` |
| `hasState(?s, "on")` | `MotionSensor( hasState == "on" )` |
| `locatedIn(?s, ?r)` (first occurrence of `?r`) | `$r : locatedIn` (binds `$r`) |
| `locatedIn(?l, ?r)` (`?r` already bound) | `Light( locatedIn == $r )` (join) |
| `swrlb:lessThan(?lx, 20)` | `LuxSensor( measuredLux < 20 )` |
| `^` | new line (implicit AND) |
| `-> OccupiedRoom(?r)` | `then insertLogical( new OccupiedRoom( $r ) );` |
| *(not expressible)* | `not SuppressedAction( device == $l )` |

Example — rule R3:
```
SWRL:  OccupiedRoom(?r) ^ DarkRoom(?r) ^ Light(?l) ^ locatedIn(?l, ?r) -> DesiredOn(?l)

DRL:   rule "R3 Occupied and dark => desire light on"
       when
           OccupiedRoom( $r : room )
           DarkRoom( room == $r )
           Light( locatedIn == $r, $l : id )
       then
           insertLogical( new DesiredOn( $l ) );
       end
```

---

## 3. The scenario

`SmartHomeApp` builds three rooms and then changes the sensors step by step, calling
`fireAllRules()` after each change.

| Room | Initial facts |
|---|---|
| livingRoom | motion1 = on, lux1 = 12, lamp1 = off, state normal, last motion 0 min (slide 28) |
| bedroom | motion2 = on, lux2 = 5, lamp2 = off, state **quiet** |
| kitchen | motion3 = off, lux3 = 300, lamp3 = **on**, last motion **45** min |

| Step | Change |
|---|---|
| 0 | insert everything |
| 1 | motion1 → off |
| 2 | livingRoom lastMotionMinutes → 40 |
| 3 | motion1 → on again, but lastMotionMinutes still 40 (stale data) |
| 4 | lastMotionMinutes → 0 |
| 5 | bedroom state quiet → normal |

**Before running**, predict for each step which facts are derived and which lights change. Then run and compare.

---

## Exercises

The exercises are in the lab slide deck (`drools_smart_home_slides`), together with a short
introduction to Drools, its execution cycle and rule priorities.
