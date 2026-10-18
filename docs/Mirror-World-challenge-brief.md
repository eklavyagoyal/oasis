# Mirror World: a synthetic defence scenario generator

*16 October 2026 · Jakub Cerny*

Every new defence product is built on data, but data is scarce, and no company makes good, cheap synthetic data that can train models and test scenarios. Your goal is to change that. Be creative: a perfect system won't be built in a day, and a good idea is much better than nothing. The tactical side doesn't matter. We are going to focus on aerial scenarios.

## The challenge

Build a system you can prompt or configure in any way you see fit, to create a random defence scenario (drones just casually flying through the scenario is enough, but again, maybe other teams will be more creative?). The only restriction: you are watching something in the air (drones, UAVs, planes) with sensors. The system produces the data those sensors would have recorded, plus the truth of what really happened. Set it somewhere real in Ukraine, with real terrain, because that is where the need is. A scenario can last anything from a few minutes to a few hours, but less than a day.

We don't need tactical precision. What matters is that every piece of data you generate is faithful to the scenario behind it: if a drone is 2 km north of a radio receiver and behind a hill, its bearing and signal strength should show it. Don't aim for perfection, because nobody has achieved it yet. Be creative instead. If we have data about the drone, the timestamps of any image or signal trace you generate have to be in sync with each other. Just have fun with it.

## What you hand in

- Your code, as a GitHub repository: a working generator that takes a prompt or a configuration and gives back a scenario. The repository is your main output. An interface is nice, but it doesn't make up for missing ideas.
- For each scenario: the truth (where everything really was), each sensor's data in a realistic-ish format, and which object every record came from. All formats can be completely made up. Claude or ChatGPT will probably provide something realistic if you are nice to it. TAK is a good inspiration.
- A short presentation of what you built and why it is better than asking Claude for it in one go.

## Which sensors

Apart from signal intelligence, which is always present, it's your choice, so be creative. Radio signals done well, with real physics behind them (propagation, terrain, interference), are worth more than ten different data feeds. Add drone telemetry, radar, Remote ID, microphones, cameras, satellites, air traffic or anything else that shows realism best (maybe even written reports?). The one thing every scenario must include is the signal trace.

## How we judge

A jury scores creativity and functionality equally, and the final presentation counts too. This is an unsolved problem that people would pay for, so do your best.

## Resources

Use anything you like: open data, simulators, Claude or any other AI tool. Resources (from page 2) lists a starting set; it is an example, not a limit nor a requirement. We can't share Psylone's own data, sorry. Unsure about something, like whether you need real radio hardware? Ask Claude; whatever the answer, it won't make or break your project.

## A realistic setup

A very basic setup has at least two signal receivers a few kilometres apart, so that their bearings cross and give a position. Here is one that could be real: 10 km of farmland and a river valley in central Ukraine, at dusk in November, with a light westerly wind. **THIS IS NOT REQUIRED, THIS IS JUST AN INSPIRATION.**

| What | Where | Gives you |
|---|---|---|
| Two radio receivers | on high ground, 6 km apart | the drone's signal (frequency, strength, direction) as TAK events |
| A drone | flying over the fields, hidden from one receiver by a ridge for two minutes | the thing everyone is watching |
| A camera | on the first receiver's tower | a picture of the drone at the same moment |
| A satellite | passing over once that day | an image of the area at the time of the pass |

## Resources

A short starting set, not a requirement, just a bunch of things to consider. For basically anything, ask Claude, it will provide realistic answers, the technicalities are not the priority here. A signal trace in TAK's format is good enough, and a picture or a satellite image is a bonus.

> THIS CAN BE BADLY VIBECODED WITH ONE PROMPT, SHOW SOME CREATIVITY AND INTERESTING IDEAS

### 1. The signal trace

An example, not a format to copy. A drone's 2.4 GHz video link is heard by two receivers, and their crossed bearings give a rough position. Written as a TAK event (Cursor on Target, the XML that TAK reads), it looks like this:

```xml
<event version="2.0" uid="sig-0007" type="a-u-A" how="m-r"
       time="2026-11-03T14:02:07Z" start="2026-11-03T14:02:07Z"
       stale="2026-11-03T14:03:07Z">
  <point lat="49.3765" lon="31.1870" hae="250" ce="150" le="50"/>
  <detail>
    <contact callsign="Unknown drone, 2.4 GHz"/>
    <remarks>Video link heard by RF1 and RF2, position from crossed bearings</remarks>
    <__signal sensor="RF1" freq_mhz="2437.5" power_dbm="-80.6" bearing_deg="1.8"/>
  </detail>
</event>
```

The answer key says where the drone really was at that moment, for example: drone_07, 49.3754 N, 31.1882 E, 120 m above ground. The estimate above is about 150 m off, as a real one would be.

*Illustration described in the brief: a map of farmland and villages in central Ukraine. Bearings from RF1 and RF2 cross near the drone; a red circle marks the estimate and a green cross marks the truth. Background: Sentinel-2, 3 September 2025, contains modified Copernicus Sentinel data.*

How to get it: place your drones and receivers, compute each bearing and signal strength from their positions (Claude can write the maths), write every detection as a TAK event with pytak, and watch them on a map in a TAK app such as ATAK-CIV.

### 2. A camera picture

*Illustration described in the brief: a synthetic frame from a camera next to RF1, at the same timestamp. At 2,140 m the drone is about 6 pixels wide, so the detector is unsure (0.41).*

*Illustration described in the brief: two rendered frames of a delta-wing drone against an overcast sky, close up and farther away. The farther it is, the fewer pixels it covers and the harder it is to recognise.*

How to get it: put a 3D drone model (for example from Sketchfab) into a scene and render it with BlenderProc in Blender or with Colosseum in Unreal, or ask an image model. Then add noise, blur and compression so it looks like a real camera.

### 3. A satellite image

*Illustration described in the brief: left, the real area around the scenario, 12 km across, as Sentinel-2B saw it on 3 September 2025 at 09:06 UTC. At 10 m per pixel you see fields, forest and villages, but not the drone. A bigger one could potentially be seen.*

*Illustration described in the brief: right, the same idea at very high resolution, 30 cm per pixel, like the best commercial satellites. A synthetic 2.5 m delta-wing drone was added at its true size: it covers about 8 by 12 pixels, and its colours are slightly smeared because a satellite captures each colour a fraction of a second apart while the drone moves. The yellow circle and the zoomed box show where it is. Aerial photo: Mykola Fedotov via OpenAerialMap, CC BY 4.0, resampled to 30 cm.*
