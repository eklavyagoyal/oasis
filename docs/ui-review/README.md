# Console visual review

Three browser review rounds were captured at 1440×900 and 1920×1080 using Chromium with SwiftShader and the existing Ros valley output.

| Round | Finding | Revision |
| --- | --- | --- |
| 1 | The island clipped the near edge; full-height rails pushed the stream and scenario loader below the viewport. The initial clock selected an earlier fix, before the first IQ capture. | Increased camera range, opened at the specified 14:02:07 UTC beat, gave key moments their own scrolling area, and reduced panel spacing. |
| 2 | Setting native `loading=lazy` on a hidden selected image prevented its request. The receiver-wide density strip obscured one object's RF2 gaps because other signals continued. | Load only the selected image eagerly, while keeping other media unloaded. Added an explicit all-signals/selected-object density control. |
| 3 | Media and density were legible. The large-screen near corner still needed more air, and the header had room for the UTC readout. | Reframed the island, clipped it to the actual scenario footprint, added a header clock, and retained aged selected-object fixes with their age labelled. |

Final captures are in `../screenshots/`. Intermediate `pass-*-1440.png` and `pass-*-1920.png` files preserve the iterations. The initial passes correctly showed an unscored audit state. An audit arrived during final integration; the delivered audit screenshot reflects the exported snapshot: 6 passes, 1 failure and 3 skips (6/10), with the missing baseline still unscored. Upstream audit output changed during integration; the console displays the supplied result without altering it.

The final production browser check reports no application exceptions or console errors. SwiftShader's driver emits performance warnings during screenshot readbacks; these are not application failures or evidence of device frame rate. No physical MacBook Air benchmark is claimed.
