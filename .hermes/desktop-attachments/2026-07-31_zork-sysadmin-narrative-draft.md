# Sysadmin Zork — Narrative Draft (Light Sysadmin-Noir)

> Companion to `2026-07-31_zork-sysadmin-game-design.md`. This is the **prose draft** — prologue briefing, Tier 0 tutorial, and all five Tier 1 levels. Voice: hard-boiled night-shift admin. Dry, terse, a wink under the exhaustion. The metaphor stays thin enough that the real Linux task is always visible underneath.

---

## Voice Guide (keep this consistent)

- **Narrator = you, second person, past-midnight.** "You" are the new junior admin. The narrator is your own inner monologue: tired, wry, competent-under-fire, and running on fumes and spite.
- **Sentence rhythm:** short. Fragments allowed. Let a beat breathe, then land a longer line like a slow exhale of smoke. Atmosphere first, then the task — but the task always arrives.
- **Noir furniture, laid on thick:** cold coffee gone to skin. The rack fans breathing like something asleep and dangerous. Fluorescent light that buzzes at a frequency designed to make men confess. Rain on the fourteenth-floor glass. A pager that won't die. The city out there not caring whether the servers live. Every terminal a lonely window lit at 3 AM.
- **The wink:** the drama is deadly serious; the stakes are... a web server. Live in that gap. Describe a dangling symlink like a body in an alley, then remember it's a symlink. Never break to say "this is silly" — play it straight and let the reader laugh.
- **Never fog the task.** Every incident names, in plain terms, what's actually broken. Metaphor is the trench coat; the command is the body underneath. Decorate freely, hide nothing.
- **GREERSON — the man you love to hate.** The senior admin who walked out mid-shift and never came back. Not a wise mentor — a **legend in his own mind and a disaster in everyone else's.** Every fire you fight tonight has his fingerprints on it: the passwords on sticky notes, the configs "he'd get to later," the undocumented everything. He leaves notes — smug, unhelpful, always one step ahead and zero steps present — that read like a man who thinks he's doing you a favor by making you clean up after him. You come to hate him a little. Then a lot. He is never in the room. That's the point.
- **Recurring cast:** GREERSON (the absent architect of your suffering), THE PAGER (the antagonist that never sleeps), THE BOX (your VM — the one honest thing in the building).

---

## PROLOGUE — "First Night on the Job"

### On first launch (before any install)

```
                    SYSADMIN ZORK
              a night-shift incident, in five acts

11:52 PM. The elevator climbs to fourteen like it's got nowhere
better to be, and neither do you. The doors part on a floor built
for machines, not men — cold, blue-lit, humming that low server-room
hymn that gets into your teeth and stays there.

Nobody's here to meet you. Of course not.

Rain works the windows over. Fourteen floors down, the city goes
about its business, indifferent as a landlord, not caring whether a
single one of these servers sees morning. Up here it's just you, the
racks breathing in the dark, and a desk with your name taped to the
edge. Spelled wrong. Somebody's idea of a welcome.

On the desk: a monitor still warm from the last poor soul who sat
here. A coffee gone cold enough to grow a skin. And a sticky note,
peeled and re-stuck a dozen times, in a slanted hand you'll come to
know and loathe:

    "Kid — congrats, the shift's yours. Something came up. Big.
     Can't talk about it. You'll figure the place out — I always
     did, and nobody handed ME a note. Build your own box first;
     I'm not letting a rookie breathe on prod. Keys, ISO, coffee:
     drawer. Try not to burn it down before sunrise.
                                          — G.

     P.S. The coffee's yours. I don't drink the cheap stuff."

You read it twice. You dislike him immediately.

The drawer holds an ISO, a spare key, and — because the universe
has a sense of humor — a second cold coffee.

Welcome to the night shift. Somewhere out there, GREERSON is not
answering his phone. In here, you're going to build a server.
```

### Prologue Step 1 — Hypervisor check

```
Every admin worth the title keeps a box of their own. A place to
break things where breaking them doesn't cost anybody their Saturday.
GREERSON never believed in that. GREERSON tested in prod. You are
going to be better than GREERSON — it's a low bar, but you have to
start somewhere.

Before you can cut steel you need somewhere to run a virtual machine.
A hypervisor. We're using VirtualBox — free, runs anywhere, and it
doesn't ask questions it doesn't want answered.

  > Checking whether VirtualBox is installed...
```

- **If present:** `VirtualBox is on the machine. One thing in this building that works on the first try. Savor it.`
- **If absent:**
```
  Not installed. No shame in it — nobody's born knowing.

  Grab it here:  https://www.virtualbox.org/wiki/Downloads
  Install it, then come back and hit ENTER. I'll wait.
  Waiting is most of the job. GREERSON never learned that either.
```

### Prologue Step 2 — The spec sheet

```
Taped inside the drawer, under the spare key, there's a build sheet.
GREERSON's handwriting again — because god forbid the man document
anything in a wiki like a professional. Still. The numbers are right,
even if the ego isn't. Here's what your box needs to be:

    CPU .......... 2 cores
    Memory ....... 2048 MB  (4096 if your host can spare it)
    Disk ......... 20 GB
    Network ...... NAT or Host-Only  (NO shared folders — this box
                   stays quarantined from your real machine. GREERSON
                   "didn't see the point" of isolation. Ask the last
                   guy how that worked out. You can't — he left too.)
    OS ........... Rocky Linux or AlmaLinux, minimal ISO

Download the ISO if you haven't:
    Rocky ....... https://rockylinux.org/download
    Alma ........ https://almalinux.org/get-almalinux

Build the VM in VirtualBox to those specs, attach the ISO, and boot
it. When you hit the installer's welcome screen — that blue Anaconda
menu, glowing like a confession booth — come back and hit ENTER.
```

### Prologue Step 3 — The install (guided, hands-on)

```
This next part you do with your own two hands. I call the shots;
you make the clicks. Nobody automates their way into knowing this —
GREERSON tried, once, with a script he never tested, and that's a
story for a night when we've both had more coffee.

Work down the installer. Slow is smooth. Smooth is home by sunrise.

  [ ] Language & Keyboard — whatever gets you typing fastest.
  [ ] Time & Date — set your timezone. Picture future-you, hunched
      over a log at 4 AM, trying to line up an outage against
      honest timestamps. Do that poor bastard a favor now.
  [ ] Installation Destination — this is the one that matters. This
      is where GREERSON always got lazy and let the machine decide.
      Not you. Choose CUSTOM partitioning and lay it out like an
      adult who intends to still have a job in the morning:
          /boot   1 GB     (standard partition)
          swap    2 GB
          /       the rest  (LVM — Tier 3 will kiss you for it)
  [ ] Root Password — set it. Then put it somewhere that is not,
      under any circumstances, a sticky note on a monitor. GREERSON's
      root password is, at this moment, legible from the hallway.
  [ ] User Creation — make a user named 'student'. Tick "Make this
      user administrator." That checkbox is your sudo. Guard it.
  [ ] Software Selection — Minimal Install. No desktop. We're not
      here to look at wallpaper. We're here to keep a witness alive.

Begin installation. Let it grind. Reboot when it's done, eject the
ISO, and log in once as 'student' just to prove to the universe
that you exist.

Hit ENTER when you're eye to eye with a fresh login prompt.
```

### Prologue Step 4 — Enable SSH (the handshake)

```
Last thing before we're partners: I need a way in. A door I can
knock on without walking fourteen flights every time something
catches fire. That door is SSH, and right now it's shut.

On the box, become root and open it:

    sudo systemctl enable --now sshd

'enable' so it comes back after every reboot. '--now' so it starts
this second. Two birds. GREERSON would've done it in three commands
and forgotten the 'enable.' Then wondered, every Monday, why the
door was locked again.

Now find the box's address so I know where to come knocking:

    ip a

Somewhere in that output is an inet line that isn't 127.0.0.1 —
that number is your box, out on the wire, waiting for me.
```

- **Prompt:** `VM address:` … `SSH port [22]:`
- Then the engine connects, installs its key, verifies sudo.

```
  > Knocking on 10.0.2.15:22 as 'student'...
  > Somebody's home. Installing my key so I quit rattling the
    handle like a stranger every time I visit...
  > Testing sudo... there it is. The keys to the kingdom, and
    unlike GREERSON, you didn't leave them on the desk.
  > Taking a snapshot. This is your box — clean, honest, and
    unbroken. Look at it while it lasts, because it won't.

  Snapshot 'clean-baseline' saved.
```

### Prologue — Complete

```
12:40 AM. You've got a server, a seat on the network, and a senior
admin who is somehow, impossibly, still not picking up his phone.

You look at the box humming quietly in its window. The one thing in
this whole rotten building that did exactly what it was told tonight.
You're already fond of it. That's a mistake, and you know it.

The pager on the desk buzzes. Once. Sharp. Like it cleared its
throat to get your attention.

Then it starts screaming.

Your shift starts now.

                                        [ Tier 0 unlocked ]
```

---

## TIER 0 — "How to Survive a Shift" (tutorial)

### t0_l1 — First Shift

**Intro:**
```
Before the real fires start, learn where the extinguisher's kept.

The pager's still screaming, but here's a secret: it can wait ninety
seconds while I teach you to not die. The box is clean. Nothing's
wrong with it yet. This is the only calm you get tonight, so use it.

Four words keep you breathing on nights like this:

    look    — I re-read you the situation. For when the dark closes in.
    hint    — Stuck? I lean in and whisper. Costs you points. Pride's
              the cheapest thing in this building; spend it freely.
    map     — The whole night laid out: what's done, what's still
              locked behind you, what's waiting in the dark ahead.
    check   — You tell me it's fixed. I go look for myself. I've been
              lied to by better men than you — GREERSON, mostly — so
              I don't take it on faith. I take it on the box.

Everything else you type drops straight into the box. Real shell.
Real Linux. Real consequences. I'm just the voice in your ear and
the hand on your shoulder.

Your first job's a mercy. Prove you can touch the box and leave a
mark: drop a file called 'badge' in your home directory. Then say
'check'.

    (Cold hands? `touch ~/badge` and it's done.)
```

**Objectives:**
- Create a file named `badge` in the `student` home directory
- Run `check` to confirm

**Victory text:**
```
There it is. `~/badge` — your name carved into the wall, first mark
of a long night. Small thing. Means everything.

Look at what you just did, because it's the whole game in miniature:
you reached into a real machine, changed something true about it,
and I checked reality instead of clapping for your say-so. That's
the deal between us. You do the work; the box tells me if it's real.
Everything after this is the same loop with the flames turned up.

The pager, which never actually stopped, somehow gets louder.  (+50)

                                        [ Tier 1 unlocked ]
```

**Hints:**
1. "This one's a freebie. The `touch` command creates an empty file."
2. "`touch` followed by the path. Your home directory is `~`."
3. "Type exactly: `touch ~/badge` — then type `check`."

---

## TIER 1 — "Navigation & Files"

> Five incidents. Each one real, each one solvable with the box in front of you. The night gets darker as you go down.

### t1_l1 — Lost in the Filesystem

**Intro:**
```
The pager's message is four words, all caps, no punctuation, because
the morning crew types like the building's on fire:

    CANT FIND THE VAULT

No path. No context. No breadcrumb. Classic GREERSON — he carried
the whole layout of this filesystem around in his head like a man
hoarding the only map in a maze, and when he walked out he took it
with him. Documentation was beneath him. Documentation is for people
who plan on being replaceable.

Here's what you can piece together at 1 AM: somewhere on this box
there's a directory the deploy team calls the vault —
/srv/company/vault. They swear it's there. They also swore last
month's outage "resolved itself," so you'll trust them exactly as
far as you can verify.

Get yourself to it. Stand inside it. Then leave proof you were the
one who found it in the dark — drop a file named 'found' in the
vault, so the morning crew knows a professional walked through here
while they slept.

You've got a shell and a whole tree to climb. First rule of not
getting lost: always know where you're standing.
```

**Objectives:**
- Navigate to `/srv/company/vault`
- Create a file named `found` inside it

**Victory text:**
```
`/srv/company/vault/found` — signed, dated, and witnessed by nobody
but the hum of the racks.

You found your footing in a filesystem you'd never seen, with no map
and no help, using nothing but your own two feet and an honest `pwd`.
That's the whole art, right there: before you throw a single punch,
you know exactly where you're standing. GREERSON never wrote it down
because he thought knowing the way made him important.

It didn't. It just made him a single point of failure with an ego.
You just proved you don't need his map.

The pager falls quiet. Enjoy the silence. It's rented, not owned. (+100)
```

**Hints:**
1. "Lost is just not knowing where you are. `pwd` prints your current directory. `ls` shows what's around you."
2. "You can walk there in one step with an absolute path: `cd /srv/company/vault`. Absolute paths start from `/` and never lie about where they go."
3. "`cd /srv/company/vault`, then `touch found`. Confirm with `ls` before you `check`."

---

### t1_l2 — The Hidden File

**Intro:**
```
The pager coughs up something almost human this time. A note,
forwarded from GREERSON's old work account, timestamped three
minutes before he vanished:

    "RECOVERY CODE IS WHERE YOU LOOK BUT DONT SEE"

Even gone, the man can't resist a riddle. Can't just leave a
password in a vault like a functional adult — has to make it a
scavenger hunt, has to make you earn the privilege of cleaning up
his mess. You can hear the smirk through the screen.

But the riddle gives it away, because GREERSON was never as clever
as he thought. "Look but don't see" — on a Linux box that's one
thing and one thing only: a dotfile. A file whose name starts with
a '.', sitting in plain sight in your own home directory, politely
invisible to any lazy `ls` that doesn't know to ask for more.

Find the hidden file in your home directory. Inside it: a recovery
code. Read it, then write that code — just the code, nothing else —
into a file called 'answer' in your home directory.

The things that matter most are usually the ones somebody hoped
you wouldn't look hard enough to find. Story of this whole building.
```

**Objectives:**
- Find the hidden dotfile in `~` containing the recovery code
- Write the recovered code into `~/answer`

**Victory text:**
```
You saw what was sitting there the whole time. The code checks out,
copied clean into `~/answer`, no smirk required.

Hidden was never gone. Half this job is just knowing to add the `-a`
— to make a system show you the things it tucks politely out of
sight. Configs. Credentials. The quiet truth of how a machine really
behaves when it thinks nobody's looking. All dotfiles, in their way.

Somewhere, wherever he's hiding, GREERSON is annoyed you cracked it
this fast. You hold onto that feeling. It's warmer than the coffee. (+120)
```

**Hints:**
1. "A plain `ls` won't show it. Files starting with a dot are hidden. What flag makes `ls` show *all* files?"
2. "`ls -a ~` reveals the dotfiles. Find the one that doesn't look like standard shell config, and `cat` it to read the code."
3. "Read the file with `cat`, copy the code, then: `echo 'THECODE' > ~/answer` (swap in the real code). Then `check`."

---

### t1_l3 — Needle in the Haystack

**Intro:**
```
3:14 AM. The hour when bad decisions come home to roost.

The web app is bleeding debug output straight to real customers —
stack traces, internal file paths, the guts of the machine spilled
across the screen for anyone with a browser and bad intentions. The
kind of thing that wakes the security team up furious and looking
for a name to put in the incident report.

The name should be GREERSON. It's always GREERSON. Somewhere under
/etc/app he flipped DEBUG mode on — "just to check something," you
can hear him say it — and then did what he always did: got bored,
wandered off, never flipped it back. That was probably weeks ago.
It's been quietly hemorrhaging ever since.

Here's the shape of your hell: there are hundreds of config files
under /etc/app. Exactly one of them carries the line
    DEBUG=on
where every sane bone in this system wants it to read
    DEBUG=off

One line. Hundreds of files. And you are absolutely not opening
them one at a time — that's how the night wins. You're going to
hunt. Find the guilty file. Flip it to off. Touch nothing else;
the other configs are innocent and the morning crew notices sloppy
work the way sharks notice blood.
```

**Objectives:**
- Locate the config file under `/etc/app` containing `DEBUG=on`
- Change that line to `DEBUG=off`, leaving all other files untouched

**Victory text:**
```
One line, buried in a haystack of hundreds, and you dragged it into
the light. DEBUG's off. The stack traces die mid-sentence. Somewhere
across town a security analyst rolls over, unaware of how close the
night came to their pager, and sleeps the sleep of the oblivious.

You didn't read every file. You asked the right question and let
`grep` do the reading — which is the entire difference between an
admin and a martyr. GREERSON left this landmine armed for weeks
because he never learned to hunt; he only ever wandered.

You hunt. Remember that about yourself.                  (+150)
```

**Hints:**
1. "You don't search by hand. `grep -r` searches recursively through every file in a directory. What are you searching for?"
2. "`grep -rn 'DEBUG=on' /etc/app` finds the file and the line number. `-n` gives you the line."
3. "Once you know the file, edit it (`vi`, or `sed -i 's/DEBUG=on/DEBUG=off/' <file>`). Verify with `grep` again, then `check`."

---

### t1_l4 — The Symlink Maze

**Intro:**
```
The deploy pipeline's dead in the water, and the error it's choking
on reads like a bad joke:

    No such file or directory: /srv/app/current

Except /srv/app/current is right there. You can see it sitting in
`ls`, bold as a liar at a funeral. It's just... glowing wrong. Red,
if your terminal's got the decency to color it — the particular red
of a thing that points somewhere that isn't there anymore.

Here's the con: 'current' was never a real directory. It's a
symlink. A signpost. A note pinned to the filesystem that reads
"the live release is THAT way," and it's supposed to point at
whichever version of the app should actually be running. But
somebody shipped a new release, deleted the old one out from under
the sign, and left the arrow pointing proudly into an open grave.

That somebody was GREERSON. The commit message just says "cleanup."
The man's idea of cleanup was deleting evidence.

The real releases live in /srv/app/releases. Find the one that
actually exists — the one with a body still in it — and repoint
'current' at it so the pipeline can find its way home.
```

**Objectives:**
- Identify the valid release directory under `/srv/app/releases`
- Repoint the `/srv/app/current` symlink to that release

**Victory text:**
```
The signpost points at solid ground again. 'current' resolves, the
pipeline exhales a breath it's been holding for hours, and the deploy
rolls forward like the grave was never there at all.

A symlink's a beautiful thing right up until it isn't: just a note
that says "look over there," pointing with total, cheerful confidence
— even when "over there" is a hole in the ground. You learned to
check where the arrows actually land before you trust them. `readlink`.
`ls -l`. Never follow a thing off a cliff just because it's sure of
itself. GREERSON was always sure of himself, too.

Look where that got him.                                 (+150)
```

**Hints:**
1. "`ls -l /srv/app` shows where `current ->` points. A dangling symlink points at something that no longer exists. What's actually in `/srv/app/releases`?"
2. "List the real releases: `ls /srv/app/releases`. One of them is the live one. You need to recreate the link to point there."
3. "Force-repoint the symlink: `ln -sfn /srv/app/releases/<the-real-one> /srv/app/current`. Verify with `ls -l`, then `check`."

---

### t1_l5 — Redirect the Flow

**Intro:**
```
Last fire of the night, and of course it's paperwork. The cruelest
kind — the kind with no flames, just volume.

The overnight batch job ran without supervision (GREERSON set it up
that way, naturally — logging was a problem for future people) and
vomited forty thousand lines into /var/log/batch/run.log. Somewhere
in that avalanche of noise are the lines that actually matter: every
one stamped ERROR. The morning report needs them pulled clean —
just the errors, each unique one counted, sorted so the worst
repeat-offender sits proud at the top.

Nobody alive is going to read forty thousand lines. Not you, not the
morning crew, and certainly not GREERSON, who is currently reading
nothing but a cocktail menu somewhere warm. So you won't read them
either. You'll build a machine out of pipes and redirection that
reads them for you: filter the noise, tally what's left, and pour
the result into /var/reports/errors.txt.

Make the machine do the reading. That is, when you get down to it,
the entire reason we built the machine.
```

**Objectives:**
- Extract `ERROR` lines from `/var/log/batch/run.log`
- Produce a unique, count-sorted list written to `/var/reports/errors.txt`

**Victory text:**
```
Forty thousand lines of midnight noise, boiled down to a report a
tired human can read over a coffee that's actually hot for once.
/var/reports/errors.txt — clean, counted, sorted, worst-first,
signed by nobody but the pipe that did the work.

And that's the secret they don't put on the certification: you
didn't do that job. You plumbed it. `grep` to filter, `sort` and
`uniq` to tally, a single '>' to pour it where it belongs. A good
admin is mostly a plumber who bills better and sleeps worse. The
pipe is the most honest tool you own — data in one end, sense out
the other, no ego in the middle.

Which is more than anyone ever said about GREERSON.

4:58 AM. The rain's quit. The racks hum their same cold hymn. And
the pager — for the first time since 11:52 — has absolutely nothing
to say to you.                                           (+150)

                              [ TIER 1 CLEARED — badge earned ]
```

**Hints:**
1. "Chain of tools, joined by pipes `|`. Start by pulling only the error lines: `grep ERROR /var/log/batch/run.log`."
2. "The classic tally pipeline: `grep ERROR ... | sort | uniq -c | sort -nr`. `uniq -c` counts, `sort -nr` puts the biggest first."
3. "Full line: `grep ERROR /var/log/batch/run.log | sort | uniq -c | sort -nr > /var/reports/errors.txt`. Make sure `/var/reports/` exists first (`mkdir -p`). Then `check`."

---

## Closing Beat (end of Tier 1, teaser for Tier 2)

```
5:31 AM. The sun comes up grey and cheap over the parking lot,
the color of a monitor that's been left on too long. Your first
shift: survived. Five fires. Five saves. One badge you can actually
hold up to the light.

You've earned the right to hate this job properly now. That takes
a full night.

On the desk, where the second cold coffee used to be, there's a new
sticky note. Same slanted hand. Fresher ink — which means at some
point tonight, while you were up to your elbows in his messes,
GREERSON was HERE. In the building. And didn't say a word.

    "Not bad, kid. You can find things now. Color me mildly
     surprised. Next you'll learn who's allowed to TOUCH the
     things you find — permissions, users, the whole locked-door
     circus. It's a disaster down there. You're welcome, by the
     way; consider it hands-on training. Get some sleep first.
     The permissions don't fix themselves.
     Believe me. I checked. Once. In 2019.
                                                        — G.

     P.S. You spelled your own name right on the badge. Progress."

You read it three times. Somewhere under the exhaustion and the
low, righteous burn of being used as a mop, a worse feeling sets in:

You're starting to understand how he thinks.

You still don't know where GREERSON went. But for the first time
all night, staring at that ink still tacky to the touch, you're
dead certain you could find out.

And you're going to.

                                        [ Tier 2 awaits ]
```

---

## TIER 2 — "Users & Permissions"

> The second shift. You know the building now. You know the coffee's a lie and the pager's a liar and GREERSON is the biggest liar of all. Tonight you learn who's *allowed* to touch what — and just how many locks one absent man can leave jammed behind him.

### Tier 2 — Opening beat

```
9:04 PM. You came back. God help you, you came back.

Slept through the daylight like a vampire with a pension, and now
here you are again — fourteen floors up, same cold blue hum, same
desk with your name spelled wrong. Somebody could've fixed the tape
in twelve hours. Nobody did. This place doesn't fix things. That's
what it keeps you for.

The pager's already awake. It's been awake. And tonight its
complaints all rhyme: can't write, can't read, can't sudo,
permission denied, permission denied, permission denied.

Last night you learned to FIND things in the dark. Tonight you
learn who's allowed to TOUCH them — the whole ugly bureaucracy of
users, groups, and the little rwx locks hung on every door in Linux.
GREERSON ran this place like he was the only person who'd ever need
a key. Turns out other people work here. Turns out that matters.

Time to go pick some locks he left jammed.

                              [ Tier 2, Level 1 unlocked ]
```

---

### t2_l1 — The Door With No Handle

**Intro:**
```
First rhyme of the night: the nightly backups aren't running. Haven't
been, for who knows how long. The one job on this box whose entire
purpose is to save everyone's skin, silently doing nothing in the dark.

You find the script fast — /usr/local/bin/nightly-backup.sh, right
where it should be. The code's fine. The cron entry's fine. But when
anything tries to RUN it, the box just shrugs:

    Permission denied

Here's the thing about a file on Linux: existing isn't enough. A
script has to be marked executable, or the system treats it like a
note nobody's allowed to act on — a door with no handle. Look at it
with `ls -l` and you'll see the permission string: who can read it,
write it, and crucially, run it. Right now, nobody can run it.

GREERSON wrote this script, saved it, tested it "in his head," and
never once chmod'd it. It's sat here for months, a fire extinguisher
bolted shut behind glass.

Give the door a handle. Make the script executable, so the owner can
finally run the thing.
```

**Objectives:**
- Make `/usr/local/bin/nightly-backup.sh` executable (at least for its owner)
- Confirm the executable bit is set in `ls -l`

**Victory text:**
```
`-rwxr-xr-x`. There it is — that little `x`, the difference between
a script and a suggestion. The backup job fires on the next tick and
actually does its job for the first time since GREERSON blessed it
with his untested confidence.

Permissions aren't decoration. Read, write, execute — three little
switches on every file, deciding not what a thing IS but what the
world is allowed to DO with it. A perfect script nobody can run is
just a very confident text file. You just taught the box the
difference.

One lock down. The pager's got a whole ring of them.        (+100)
```

**Hints:**
1. "`ls -l /usr/local/bin/nightly-backup.sh` shows the permission string. See how there's no `x`? That's why it won't run. Executable is a permission you add."
2. "`chmod` changes permissions. To add the execute bit for everyone: `chmod +x <file>`. To be precise about the owner only: `chmod u+x <file>`."
3. "Run: `chmod +x /usr/local/bin/nightly-backup.sh`. Verify with `ls -l` (look for the `x`), then `check`."

---

### t2_l2 — Whose Box Is It Anyway

**Intro:**
```
10:47 PM. The website's up but frozen — serving pages it can't
update, a museum behind glass. Users hit 'save' and get a shrug.
The logs are a wall of the same three words you're learning to hate:

    Permission denied

You trace it to /srv/www. The web service runs as a user called
'www-data', quiet and unglamorous, whose one job is to own and edit
the files under there. Except it doesn't own them. Root does.

Because — say it with me — GREERSON. Something broke last week, he
ran a restore as root "just to get it working," and every single
file came back wearing root's name on the deed. root can touch them.
The web service, the actual thing that needs them, is locked out of
its own house. He fixed the symptom and left a landmine, which if
you're keeping score is the man's entire career in one sentence.

Ownership is two things on Linux: a user and a group. Right now both
are wrong across /srv/www. Hand the house back to the tenant who
actually lives there — set the owner AND group to www-data, top to
bottom, so the service can write again.
```

**Objectives:**
- Recursively set ownership of `/srv/www` (and everything under it) to user `www-data` and group `www-data`
- Confirm with `ls -l` that the files no longer belong to root

**Victory text:**
```
`www-data www-data`, straight down the tree. The service reaches for
its files and, for the first time in a week, the files reach back.
Pages save. The museum comes alive. Somewhere a product manager
stops drafting an angry email and never knows how close it came.

Ownership is the deed, not the lock. `chmod` decides what the
permissions ARE; `chown` decides WHOSE they are — and a service can
have every permission in the world and still be helpless if the
files wear someone else's name. GREERSON confused "it works for me,
root" with "it works." Those are different sentences. You know that
now, down in your bones.                                    (+130)
```

**Hints:**
1. "`ls -l /srv/www` — see how everything's owned by `root root`? The service runs as `www-data`. Ownership is set with `chown`, and it can take `user:group`."
2. "`chown` changes ownership. To do a whole tree, it needs to be recursive: the `-R` flag. Format: `chown -R user:group /path`."
3. "Run: `chown -R www-data:www-data /srv/www`. Verify with `ls -l /srv/www`, then `check`."

---

### t2_l3 — The Locked Gate

**Intro:**
```
1:12 AM. The deploy pipeline needs a hand, and the hand it needs is
a user called 'deploy' — a service account whose whole life is
running a few blessed commands with sudo. Simple. Except:

    deploy is not in the sudoers file. This incident will be reported.

Worse than that. You go to look, and you can't sudo either. Nobody
can. The gate that grants elevated power on this whole box is
slammed shut and jammed, and the jam is a single fat-fingered line.

Here's the trap, and it's a nasty one: /etc/sudoers is the config
that decides who gets to become root. If it has even one syntax
error, sudo doesn't "mostly work" — it refuses EVERYONE, including
you, including the tools you'd normally reach for. GREERSON edited
it by hand last week (with `vi`, like an animal, instead of the tool
built for exactly this), botched a line, saved it, and walked. The
gate's been welded shut ever since.

There's a right way through this. `visudo` — the editor made for
this file — validates your syntax BEFORE it saves, so you can't lock
yourself out twice. And `visudo -c` will check the current file and
tell you exactly which line GREERSON broke.

Fix the sudoers file. Get 'deploy' its access back. And when you're
done, prove the gate is sound — `visudo -c` must come back clean.
```

**Objectives:**
- Repair the syntax error in `/etc/sudoers` (use `visudo`)
- Grant the `deploy` user sudo access
- Ensure `visudo -c` validates the file with no errors

**Victory text:**
```
`/etc/sudoers: parsed OK`. Four words that mean the gate swings
clean again. 'deploy' straightens its tie, runs its blessed command,
and the pipeline flows like it never seized. You back out of that
file the way you'd back out of a room with a sleeping wolf in it —
slow, grateful, and using the right door.

This is the one that teaches humility. sudoers is the single most
unforgiving config on the box: perfect or locked-out, no middle. The
lesson isn't "edit carefully." The lesson is `visudo` — a tool that
refuses to let you save a mistake, because the people who built Linux
knew that someday, at 1 AM, a tired human would try. GREERSON thought
tools like that were for people less clever than him.

The gate disagrees.                                         (+180)
```

**Hints:**
1. "Don't edit `/etc/sudoers` with a normal editor — that's how it got broken. Use `sudo visudo`, which validates before saving. First, `sudo visudo -c` will name the broken line."
2. "Open it with `sudo visudo`. Find the malformed line (often a typo'd username, missing keyword, or bad `ALL=(ALL)` clause). Fix it. To grant deploy access, a line like `deploy ALL=(ALL) ALL` does it."
3. "In `sudo visudo`: correct the broken line, add `deploy ALL=(ALL) ALL`, save & exit (visudo re-checks on save). Confirm with `sudo visudo -c` → 'parsed OK', then `check`."

---

### t2_l4 — The Members-Only Club

**Intro:**
```
2:38 AM. There's a new hire — 'jordan' — who started three days ago
and hasn't been able to do a lick of work, because every shared file
they touch says the same thing you can now recite in your sleep:

    Permission denied

But this one's different. The files under /srv/finance aren't broken.
Their permissions are exactly right: owner can do owner things, and
the 'finance' GROUP can read and write. That's the system working as
designed. The problem is jordan isn't in the finance group. They're
standing outside a members-only club with a valid reason to be inside
and no stamp on their hand.

On Linux, a user can belong to many groups, and groups are how you
grant access to a bunch of people at once without editing every file.
GREERSON created jordan's account — you can tell, because he did the
absolute minimum and not one keystroke more — and never added them to
a single group they'd actually need. Onboarding, to GREERSON, meant
"the account exists." The human attached to it was a someone-else
problem.

Get jordan into the finance group so they can finally do the job they
were hired for. Careful, though — jordan belongs to other groups too,
and you don't want to evict them from those in the process.
```

**Objectives:**
- Add user `jordan` to the `finance` group
- Ensure jordan's existing group memberships are preserved (don't replace them)

**Victory text:**
```
`jordan : jordan finance ...` — stamped, and still holding every
other stamp they came in with. The next time jordan opens a file
under /srv/finance, the door just... opens. No fanfare. Access,
when it works, is invisible. That's the point of it.

The trap you dodged is the whole lesson: `usermod -aG` — the little
`-a` for *append*. Without it, `usermod -G` doesn't ADD a group, it
REPLACES every group the user had, quietly kicking them out of
everything else. One missing letter and you'd have fixed finance
while breaking five things you couldn't see. GREERSON would've run
it without the `-a`, caused three new tickets, and blamed the tool.

You read the whole command before you ran it. That's the job.  (+150)
```

**Hints:**
1. "The files are fine; jordan just isn't in the `finance` group. Check with `groups jordan` or `id jordan`. Group membership is changed with `usermod`."
2. "The safe way to ADD a group without wiping the others is `usermod -aG`. The `-a` means append. `usermod -aG groupname username`."
3. "Run: `sudo usermod -aG finance jordan`. Verify with `groups jordan` (finance should now be listed alongside the originals), then `check`. (jordan may need to log back in for a live session, but the membership is what we check.)"

---

### t2_l5 — The Shared Table

**Intro:**
```
4:20 AM. Last lock of the night, and it's the one GREERSON should
have gotten right, because it was HIS idea.

There's a directory — /srv/shared — meant to be exactly what the
name says: a common table where the whole 'staff' group drops files
for each other. Reports, handoffs, the connective tissue of people
who actually cooperate. Beautiful concept. GREERSON announced it in
an all-hands and took the credit.

Then he set it up like this: every file someone creates in there
lands owned by that person's PRIVATE group, so nobody else at the
table can edit it. And there's no guard on deletion, so anyone can
wipe anyone's work on their way out. A shared table where you can't
touch what others put down but you CAN sweep the whole thing onto the
floor. It's been a slow-motion disaster of overwrites and mystery
deletions for weeks.

Two special permission bits fix this, and they're the capstone of
everything you learned tonight:

  - The SETGID bit on the directory (`chmod g+s`) makes every new
    file inside inherit the directory's GROUP — so the whole staff
    group can collaborate instead of each file hiding in a private one.
  - The STICKY bit (`chmod +t`) says "you can only delete files you
    own" — so nobody sweeps the table clean but the person who set
    the plate.

Set the directory's group to 'staff', then set setgid and sticky so
the shared table finally works like a shared table. Fix the thing
GREERSON took credit for and never actually built.
```

**Objectives:**
- Set the group of `/srv/shared` to `staff`
- Apply the **setgid** bit so new files inherit the `staff` group
- Apply the **sticky** bit so users can only delete their own files
- Confirm the permission string shows both bits (e.g. `drwxrws--T` / `rwxrwsrwt`)

**Victory text:**
```
`drwxrwsr-t`. Read that permission string like a sentence, because
you can, now: directory, group-writable, SETGID (`s`) so the table
shares its name with everything set on it, STICKY (`t`) so only the
owner clears their own plate. The staff group drops a file and
everyone can pick it up. Someone leaves in a huff and can't take the
whole table with them.

It works. The thing GREERSON announced and never wired up, the thing
that's been quietly eating people's work for a month — you built it
right in four commands and a genuine understanding of what those
little `s` and `t` bits actually do. Not memorized. Understood.

5:00 AM sharp. The pager exhales a long, static-filled silence, and
for the second night running, it has nothing left to say to you.

You didn't just fix his locks tonight. You understood every one of
them better than he ever did.                               (+200)

                              [ TIER 2 CLEARED — badge earned ]
```

**Hints:**
1. "Two special bits do this. First set the group: `chgrp staff /srv/shared`. Then look up SETGID (shares the group to new files) and the STICKY bit (restricts deletion)."
2. "SETGID on a directory: `chmod g+s /srv/shared`. STICKY bit: `chmod +t /srv/shared`. You can also do both octally: the leading digit `3` = setgid+sticky (e.g. `chmod 3775`)."
3. "Run: `sudo chgrp staff /srv/shared`, then `sudo chmod g+s /srv/shared` and `sudo chmod +t /srv/shared` (or `sudo chmod 3775 /srv/shared`). Verify with `ls -ld /srv/shared` — look for `s` and `t` in the permission string — then `check`."

---

## Closing Beat (end of Tier 2, teaser for Tier 3)

```
5:41 AM. Two shifts down. The sun's doing its cheap grey trick over
the parking lot again, and you're starting to think of it as an old
enemy rather than a new one. Progress, of a kind.

Your badge has weight now. Two tiers. You can find what's hidden and
you can control who touches it — which is most of what anyone means
when they say the word "sysadmin" out loud.

On the desk: another note. You expected it this time. You almost
missed it if it wasn't there. The ink's dry now — he came and went
while you worked, again, close enough to touch and gone as ever.

    "Two nights, and the locks are holding. Didn't think you had
     it. Here's the part nobody warns you about, kid: it's not the
     locks that get you. It's the things that are RUNNING. Services
     that die at 3 AM. Processes that eat the box alive. A disk
     that fills up and takes the whole night with it. That's the
     real job — keeping the living things alive.

     I'd know. I let a lot of them die.
                                                        — G.

     P.S. Stop reorganizing my sticky notes. I can tell."

You look up. The racks breathe. Fourteen floors down, a city that
still doesn't care.

But you're closer to him now. Two notes closer. And whatever's
running — or dying — down in Tier 3, you're starting to suspect
it's the thing that'll finally tell you where GREERSON went.

                                        [ Tier 3 awaits ]
```

---

## TIER 3 — "Services & Processes"

> The third shift. This is where the game's promised power arrives — real systemd, a real disk that really fills, real processes that really eat the box alive. It's also where the mystery turns: GREERSON told you he "let a lot of them die." Tonight you meet the bodies. And one of them is still warm.

### Tier 3 — Opening beat

```
8:47 PM. You didn't sleep much. Kept turning that last note over.
"It's not the locks that get you. It's the things that are RUNNING."
"I let a lot of them die." A man doesn't write a line like that
about web servers. Or — you're beginning to think — a man like
GREERSON only ever writes about web servers, because they're the
only things he ever let himself care about, and that's the whole
tragedy of him.

Either way. The pager's got a different voice tonight. Last night
was locked doors — dead things, static, waiting. Tonight everything's
in motion, and motion is where it gets dangerous. A service is a
living thing on this box: it starts, it runs, it can stall, choke,
die in its sleep, or go rabid and eat everything around it. Your job
stops being locksmith and starts being something closer to a night-
shift medic. Or a coroner.

Down in the process table, something is running that shouldn't be.
And something that should be running is very, very quiet.

Let's go find the bodies.

                              [ Tier 3, Level 1 unlocked ]
```

---

### t3_l1 — The Body in the Logs

**Intro:**
```
9:15 PM. The website's not slow. It's not erroring. It's just gone —
the flat, total nothing of a service that isn't there. curl comes
back with a dead line and a closed door:

    Connection refused

Connection refused is different from last night's permission denied.
Denied means something answered and said no. Refused means nobody's
home at all. The web server — nginx — isn't running. It's a corpse
on the floor of the process table and nobody called it in.

Here's the good news the young admins never believe until they see
it: on a systemd box, the dead leave a statement. Every service
writes to the journal as it lives and dies, and when nginx went
down it said WHY on its way out — you just have to know how to read
a dying man's last words.

Two tools, and they're the heart of this whole tier:
  - `systemctl status nginx` tells you the state of the body:
    running, stopped, or failed, and the last few lines it gasped.
  - `journalctl -u nginx` is the full autopsy — every log line the
    service ever wrote, so you can see what killed it.

Read the logs. Find out why nginx died. Then bring it back —
`systemctl start` — and confirm it's actually breathing (active,
running) before you call it a save.
```

**Objectives:**
- Inspect why `nginx` is not running (`systemctl status nginx` / `journalctl -u nginx`)
- Start the `nginx` service
- Confirm the service reports `active (running)`

**Victory text:**
```
`active (running)`. Two words, green if your terminal's kind. nginx
is back on its feet, the door's open, curl gets a real answer for
the first time in hours. You didn't just restart it blind and hope —
you read the journal, saw what dropped it, and brought it back
knowing why it fell. That's the difference between a reboot and a
diagnosis.

This is the skill that separates the medics from the button-mashers.
Anything can turn a service off and on again. A real admin asks the
body what happened first. `systemctl` for the pulse, `journalctl`
for the story. The box keeps a record of every death on it, patient
and complete — which is more courtesy than GREERSON ever showed the
things he let die.

Speaking of. Something in that journal caught your eye. A service
name you didn't recognize, logging quietly in the background. You
file it away.                                               (+130)
```

**Hints:**
1. "`systemctl status nginx` shows whether it's running and the last log lines. Look for `inactive` or `failed`. For the full story, `journalctl -u nginx` (or `journalctl -xe`)."
2. "Once you understand why it stopped, start it with `sudo systemctl start nginx`. Then re-run `systemctl status nginx` to confirm."
3. "Run `sudo systemctl start nginx`, verify with `systemctl is-active nginx` (should say `active`) or `systemctl status nginx`, then `check`."

---

### t3_l2 — The Thing That Wouldn't Stay Dead

**Intro:**
```
10:40 PM. nginx is running. You fixed it an hour ago. So why is the
pager screaming about it again?

You check. It's down. Again. You start it. It comes up, healthy,
green, fine. You exhale. Then, on a hunch you're not proud of, you
reboot the box in your head and ask the ugly question — and there it
is. nginx starts when YOU start it. But it does not come back on its
own. Every reboot, every power blip, and the service stays in the
ground until a human walks over and hauls it up by hand.

Somebody's been that human for months. You can picture him: GREERSON,
every Monday, cursing, manually starting the same three services,
never once asking why he had to. Because here's the thing he never
understood — starting a service and ENABLING a service are two
completely different verbs:

  - `systemctl start` runs it NOW. Until the next reboot.
  - `systemctl enable` wires it to boot AUTOMATICALLY, every time,
    forever, so no tired human ever has to remember.

You already learned this, once, in the dark — remember the prologue?
`systemctl enable --now sshd`? The `--now` did both at once. GREERSON
only ever did half. He started things. He never made them permanent.
Kind of his whole life, if the notes are any guide.

Make nginx permanent. Enable it so it survives a reboot on its own,
and confirm it's set to come up at boot.
```

**Objectives:**
- Enable `nginx` so it starts automatically at boot (`systemctl enable`)
- Ensure it is also currently running
- Confirm `systemctl is-enabled nginx` reports `enabled`

**Victory text:**
```
`enabled`. Such a quiet word for such a load off your back. nginx
will now claw its way up on its own after every reboot, every crash,
every 3 AM power flicker, with no human required to remember it. You
just fired the ghost of GREERSON from his own Monday-morning ritual.

Start versus enable. Now versus always. It's the difference between
doing a job and building a system that does the job without you —
which is, when you strip away everything else, the entire point of
this profession. The best admin is the one who makes themselves
unnecessary. GREERSON made himself a single point of failure and
called it job security. Look how that ended: you, here, cleaning up
a service he had to resurrect by hand every week because he never
spent the thirty seconds to `enable` it.

The unrecognized service from the journal is still nagging at you.
It's enabled. Somebody wanted THAT one to survive.          (+140)
```

**Hints:**
1. "The service runs when you start it but dies on reboot because it's not enabled. Check with `systemctl is-enabled nginx`. `start` ≠ `enable`."
2. "`sudo systemctl enable nginx` wires it to boot. To enable AND start in one step: `sudo systemctl enable --now nginx` (you saw `--now` back in the prologue with sshd)."
3. "Run `sudo systemctl enable --now nginx`, confirm with `systemctl is-enabled nginx` → `enabled` and `systemctl is-active nginx` → `active`, then `check`."

---

### t3_l3 — The Process Eating the Box

**Intro:**
```
12:03 AM. The whole box has gone slow. Not down — slow, which is
worse, because slow means something's alive and gorging. Every
command you type takes a beat too long to answer. The fans have
spun up to a whine you can hear through the floor. Something on this
machine is eating it alive from the inside.

This is a hunt, but a different kind than Tier 1. You're not looking
for a file — you're looking for a PROCESS, a running thing, and
processes hide in a table you have to know how to read. One of them
has pinned a CPU core to the wall and won't let go: some runaway
GREERSON kicked off — a debug loop, a stuck script, a "temporary
test" from three weeks ago that never got the memo to stop.

Your tools:
  - `top` (or `ps aux`) shows every process and what it's burning.
    Sort by CPU and the guilty one floats to the top, fat and obvious.
  - Every process has a PID — a number, its name in the world.
  - `kill <PID>` sends it a polite request to stop. `kill -9 <PID>`
    is the request that doesn't take no for an answer — the last
    resort, when the polite one gets ignored.

Find the process pinning the CPU. Note its PID. End it — cleanly if
it'll listen, forcefully if it won't. Give the box its lungs back.
```

**Objectives:**
- Identify the runaway high-CPU process (`top` / `ps aux --sort=-%cpu`)
- Terminate it by its PID (`kill`, escalating to `kill -9` only if needed)
- Confirm the process is gone and CPU load has dropped

**Victory text:**
```
Gone. The fans wind down from a scream to a hum, the prompt snaps
back to answering you like it respects your time again, and the load
average starts its slow slide back toward something human. You found
the thing that was eating the box, learned its name — its PID — and
ended it with exactly as much force as it required. No more, which
matters.

There's a discipline in that escalation the button-mashers never
learn. You try `kill` first — the SIGTERM, the tap on the shoulder,
the chance for a process to close its files and die with dignity.
Only when it ignores you do you reach for `kill -9`, the SIGKILL, the
one with no manners and no mercy. GREERSON `kill -9`'d everything on
reflex, from the start, and corrupted more data than he ever admitted
doing it that way. Force is a tool, not a personality.

You end things cleanly. Even his messes.                    (+150)
```

**Hints:**
1. "`top` shows live CPU use — press once and watch what's pinned near 100%. Or `ps aux --sort=-%cpu | head`. Note the PID (the process ID number) of the offender."
2. "Stop it with `kill <PID>` (sends SIGTERM, the graceful request). If it refuses to die, escalate: `kill -9 <PID>` (SIGKILL, forceful). Prefer the graceful one first."
3. "Find the PID via `top`/`ps`, run `kill <PID>` (then `kill -9 <PID>` only if it won't stop), confirm it's gone with `ps aux | grep <name>` and that load dropped, then `check`."

---

### t3_l4 — The Rising Tide

**Intro:**
```
1:51 AM. Everything's failing at once — writes, logs, the database,
even your own commands sputtering with errors that make no sense
until they suddenly, sickeningly, do:

    No space left on device

The disk is full. One hundred percent. And a full disk is a special
kind of catastrophe, because it doesn't break ONE thing — it breaks
EVERYTHING, all at once, silently, since almost nothing on a Linux
box works when it can't write. Services die mid-breath. Logs can't
even record their own failure. The whole machine seizes like an
engine run dry.

The tide came in slow and nobody was watching the water. Somewhere
under /var something has been growing for weeks — a log that never
rotated, a cache that never cleared, GREERSON's idea of "I'll deal
with it later" measured now in gigabytes. You need to find the flood
source and drain it.

Your instruments:
  - `df -h` shows every filesystem and how full it is — this is how
    you confirm which partition drowned.
  - `du -sh *` (run inside a directory) shows how much space each
    thing under it is eating, so you can follow the water uphill to
    whatever's pouring.

Find what's eating the disk under /var. Reclaim the space — clear
the offending bloat — and get the filesystem back under control so
the box can breathe and write again.
```

**Objectives:**
- Identify the full filesystem (`df -h`) and the directory/file consuming it (`du`)
- Reclaim space by clearing the offending bloat (e.g. truncating/removing the runaway file)
- Confirm the filesystem is back below capacity with free space available

**Victory text:**
```
`df -h` reads like a reprieve: the partition that was pinned at 100%
now has room to breathe, and one by one the services that seized
come stuttering back to life as they find they can write again. You
followed the water uphill with `du`, found the thing that had been
quietly flooding the box for weeks, and pulled the plug on it.

Here's the lesson that'll save a career someday: a full disk is the
outage that fakes ten other outages. Every symptom pointed somewhere
else — the database, the services, your own shell — and every one of
them was lying. The real culprit was space, and the only tools that
told the truth were `df` and `du`. When everything breaks at once,
check the disk FIRST. GREERSON never did. GREERSON saw ten alarms and
chased ten ghosts and let the real thing drown the box while he ran
in circles.

You checked the water level. You always will now.           (+170)
```

**Hints:**
1. "`df -h` shows which filesystem is full — look for the one at 100% (likely mounted at or under /var). Then `cd` there and use `du -sh *` to see what's biggest."
2. "Follow `du -sh *` down into the biggest directory repeatedly until you find the specific runaway file/log. To reclaim a live log safely, truncate it: `truncate -s 0 <file>` (or `: > <file>`) rather than deleting a file a service still holds open."
3. "Locate the hog (`df -h` then `du -sh /var/* | sort -h`), clear it (truncate the runaway log or remove the stale bloat), confirm free space with `df -h`, then `check`."

---

### t3_l5 — The Job That Runs at Midnight

**Intro:**
```
3:33 AM. You've been putting this off all night and you know it.

That service name from the journal — the one you didn't recognize,
the one that's quietly enabled, the one somebody wanted to survive
every reboot. You finally go looking for it properly, and what you
find isn't a service exactly. It's a timer. A systemd timer — cron's
modern cousin — set to fire every night at a time you'd find funny
if it didn't make the hair on your arms stand up. It's called
something bland. `sys-maintenance.timer`. Designed not to be looked
at twice.

You look at it twice.

It runs a script. The script does something small and specific and
regular, out to an address off this box, every single night, and it
has been doing it faithfully since three days before GREERSON walked
out the door and stopped answering his phone. Enabled. Persistent.
The one thing in this whole building he made permanent. The one thing
he actually finished.

You don't know yet if it's a dead man's switch, a backup nobody
authorized, or something worse. But you know it shouldn't be running
unsupervised, and you know how to stop a thing so thoroughly it can't
claw its way back at boot like nginx did:

  - `systemctl stop` ends it now.
  - `systemctl disable` stops it surviving reboot.
  - `systemctl mask` is the deadbolt — it makes the unit impossible
    to start at all, by anything, until a human deliberately unmasks
    it. For something you don't trust, mask is the answer.

Stop the timer. Disable it. Mask it shut. Then read what it's been
doing — and find out where GREERSON went.
```

**Objectives:**
- Identify and inspect the suspicious timer/unit (`systemctl list-timers`, `systemctl cat sys-maintenance.timer`)
- Stop it, disable it, and **mask** it so it cannot be started again
- Confirm `systemctl is-enabled sys-maintenance.timer` reports `masked`

**Victory text:**
```
`masked`. The deadbolt slides home. Whatever `sys-maintenance.timer`
was reaching out to do every midnight, it will not do it again — not
tonight, not at the next reboot, not until a human with the full
story deliberately turns the key. You stopped it, cut its boot
wiring, and then masked it into a locked box, because "off" wasn't
enough for a thing you didn't trust. That instinct — that some things
should be made impossible, not merely inconvenient — is the last
thing this tier had to teach you.

Then you read the script.

It's a health check. That's all. Every midnight for months it's
pinged a single outside address and reported, in one quiet line,
that this box is still alive. No data. No theft. Just a heartbeat,
sent faithfully into the dark, to an address that — you run it down —
resolves to a hospital across the river.

Somebody wanted to know, every night at 3:33 AM, that the box
GREERSON built was still breathing. Even after he couldn't come
check himself.

Oh.

Oh, you think. That's where he went.

4:44 AM. The pager is silent. The racks breathe. And for the first
time in three nights, you understand that you were never cleaning up
after a deadbeat. You were covering for a man who ran out of nights.
                                                            (+220)

                              [ TIER 3 CLEARED — badge earned ]
```

**Hints:**
1. "Find it with `systemctl list-timers --all` and inspect the unit and what it runs: `systemctl cat sys-maintenance.timer` and the service it triggers. Read the script it calls before you judge it."
2. "To fully neutralize a unit: `sudo systemctl stop <unit>`, then `sudo systemctl disable <unit>`, then `sudo systemctl mask <unit>`. Mask is stronger than disable — it makes the unit impossible to start."
3. "Run `sudo systemctl stop sys-maintenance.timer`, `sudo systemctl disable sys-maintenance.timer`, `sudo systemctl mask sys-maintenance.timer`; confirm with `systemctl is-enabled sys-maintenance.timer` → `masked`, then `check`."

---

## Closing Beat (end of Tier 3, turn toward Tier 4)

```
You sit with it for a while. The coffee's cold — it's always cold —
but you don't drink it anyway, out of something like respect.

Three nights ago GREERSON was a name you learned to curse. A deadbeat
with legible passwords and a genius's ego and a trail of half-finished
disasters you got handed like a hazing. You hated him. It was easy and
it felt good and it was, you understand now, completely wrong.

He wasn't lazy. He was leaving. Every jammed lock and unrotated log
and un-enabled service wasn't arrogance — it was a man running out of
time, triaging a life, deciding which fires he had the days left to
fight. He didn't document because he was hoping he wouldn't have to
hand it off. And when he had to anyway, he left it to a stranger with
sticky notes and a heartbeat timer pointed at his own hospital room,
because he wanted to know his box outlived him.

There's no new note on the desk tonight. You look. There won't be
another one; you know that now.

But the pager still buzzes. The city outside still doesn't care
whether these servers see morning — but you do, and you're starting
to understand that's the whole job, the actual one underneath all the
commands: somebody has to care whether the living things live.

Tomorrow night it's the network — the wires that connect this lonely
box to a world that never once called to check on it. Firewalls.
Ports. The doors that face outward.

You finish GREERSON's shift. All of it. However long it takes.

That's the job now. It was always the job.

                                        [ Tier 4 awaits ]
```

---

## TIER 4 — "Networking & Firewall"

> The fourth shift. GREERSON's ghost is laid to rest — but his final gift, that heartbeat pinging out across the river, left a light on in the dark. And something out there followed it home. This tier turns the game outward: the box stops being a patient and becomes a fortress, and for the first time you're not fixing accidents. You're fighting a person.

### The new nemesis — THE FERRYMAN

> Where GREERSON was chaos wrapped around a warm heart, the FERRYMAN is order wrapped around nothing. A patient, professional intruder who hunts for wounded systems — the ones broadcasting distress, running old software, bleeding signal into the night. GREERSON's heartbeat timer was a love letter to a box he was dying to protect. The Ferryman read it as an address. He follows heartbeats the way carrion birds follow the smell. He does not smash. He *seeps*. He leaves the lights on and the doors as he found them, and signs his work — when he signs it at all — with a single lowercase line: `// ferryman was here`. Tier 4 is him testing your walls from outside. Tier 5 is when you find out how long he's been inside.

### Tier 4 — Opening beat

```
9:22 PM. Fourth night. The desk feels like yours now, wrong-spelled
tape and all. You've stopped hating the cold coffee. You've started,
God help you, making a fresh pot.

But something's off tonight and it isn't GREERSON. The box is healthy
— you made it healthy — services up, disk breathing, everything you
fixed still holding. And yet the back of your neck won't settle,
because buried in tonight's logs is a pattern that isn't an accident.
Accidents are what GREERSON left. This is different. This has intent.

Someone is knocking on the doors of this machine. Not once. Methodically.
Port after port, night after night, patient as a tide, testing every
window to see which one you forgot to lock. And you know — the way you
know weather — that they found this box by following the one signal
GREERSON couldn't help sending: that heartbeat, going out across the
river, every midnight, saying *I'm still here, I'm still here.*

Somebody out there heard *I'm still here* and thought: **good.**

Tonight you stop being a medic. Tonight the box isn't a patient — it's
a perimeter, and there's a professional working the fence line. Time to
learn what's open, close what shouldn't be, and build a wall worth the
name before you find out exactly how patient he's been.

                              [ Tier 4, Level 1 unlocked ]
```

---

### t4_l1 — Who's Knocking

**Intro:**
```
First rule of the fence line: you cannot defend a perimeter you
haven't walked. Before you close a single door you need to know every
door that exists — every port this box is listening on, and every
outside connection currently reaching in.

Most admins never do this until it's too late. They assume they know
what their own machine is exposing. They're always wrong, and GREERSON
was wrong bigger than most: this box is listening on ports you never
opened, for services you didn't know were running, because he stood
things up over the years and never once took inventory.

Your tool is `ss` — socket statistics, the flashlight you walk the
perimeter with:
  - `ss -tlnp` lists every TCP port in LISTEN state, and the process
    behind each one. This is your door inventory.
  - `ss -tnp` shows ESTABLISHED connections — who's actually reaching
    in right now.

Walk the perimeter. Somewhere in that listing is a port that has no
business being open — something listening to the whole world that
should be listening to no one. Find the unexpected listener, identify
the process behind it, and write its port number into
/root/perimeter.txt so you've got your inventory on record.

Don't close anything yet. Tonight you're just learning the ground.
```

**Objectives:**
- Enumerate listening TCP ports and their processes (`ss -tlnp`)
- Identify the unexpected/suspicious listening port
- Record that port number in `/root/perimeter.txt`

**Victory text:**
```
There it is, written down where you can't un-know it:
`/root/perimeter.txt`, one line, one port that shouldn't be open to
the world. You walked your own fence line with a flashlight and found
the gap — not by guessing, not by assuming, but by asking the box
directly what it was exposing and making it answer.

This is the discipline nobody teaches until after the breach: know
your own attack surface before someone else maps it for you. `ss` is
how you see your machine the way an attacker sees it — a list of open
doors, each one a promise or a mistake. GREERSON never ran it once.
The Ferryman, you'd bet your cold coffee, has run it against this box
a hundred times.

Now you've seen what he's seen. That's the first time all week you've
been even.                                                  (+130)
```

**Hints:**
1. "`ss -tlnp` shows listening TCP sockets with the owning process (`-t` tcp, `-l` listening, `-n` numeric, `-p` process). Look for a port you don't recognize among the expected ones (22 ssh, 80/443 web)."
2. "Compare what's listening against what SHOULD be. An extra high port (e.g. something in the 4000–9000 range) bound to `0.0.0.0` is your suspect. Note the port number in the last column of its address."
3. "Enumerate with `sudo ss -tlnp`, find the odd port, then record it: `echo '<PORT>' | sudo tee /root/perimeter.txt`. Then `check`."

---

### t4_l2 — The Open Window

**Intro:**
```
10:48 PM. You know the ground now. Time to close the window nobody
should've left open.

That extra port you found isn't just listening — the firewall is
actively waving traffic through to it. On a RHEL box the wall is
`firewalld`, and right now the wall has a hole in the exact shape of
your problem. GREERSON, at some point, ran the lazy incantation —
threw the port wide open "just to test something," never closed it,
never wrote it down. It's been a lit window on a dark street for
months, and there's a professional outside who noticed.

`firewalld` works in zones and rules, and you speak to it through
`firewall-cmd`:
  - `firewall-cmd --list-all` shows exactly what your active zone is
    allowing — services and ports both. This is the wall's blueprint.
  - Changes come in two flavors: runtime (instant, gone on reboot)
    and `--permanent` (written to disk). Real fixes need permanent,
    followed by `--reload` to make the saved rules live.

Find the rule that's letting the world reach that port. Remove it —
permanently — and reload the firewall so the window is shut for good,
not just until the next reboot. Then confirm with `--list-all` that
the hole is gone.
```

**Objectives:**
- Inspect the active firewalld zone (`firewall-cmd --list-all`)
- Permanently remove the rule exposing the unexpected port/service
- Reload firewalld and confirm the port is no longer allowed

**Victory text:**
```
`firewall-cmd --list-all` reads clean now — the extra port gone from
the ports list, the window bricked over, and the change written to
disk so it survives every reboot from here to retirement. You didn't
just slam it shut for tonight. You made it *stay* shut, which is the
only kind of shut that counts against someone patient.

Runtime versus permanent — it's the enable-versus-start lesson wearing
a firewall's clothes. A rule that vanishes on reboot is a door you have
to keep closing by hand, and the Ferryman only needs you to forget
once. `--permanent` plus `--reload` is how you close a thing and mean
it. GREERSON opened windows and walked away. You close them and write
it down.

One window bricked. But a good burglar doesn't need the window he came
through to still be open. He just needs to already be inside.  (+150)
```

**Hints:**
1. "See what the active zone allows: `sudo firewall-cmd --list-all`. Look for the offending port under `ports:` or a service under `services:`."
2. "Remove it permanently. For a port: `sudo firewall-cmd --permanent --remove-port=<PORT>/tcp`. For a named service: `sudo firewall-cmd --permanent --remove-service=<name>`. Permanent edits need a reload to take effect."
3. "Run the appropriate `--permanent --remove-port=<PORT>/tcp` (or `--remove-service`), then `sudo firewall-cmd --reload`, confirm with `sudo firewall-cmd --list-all`, then `check`."

---

### t4_l3 — The Wrong Door Faces the Street

**Intro:**
```
12:15 AM. You closed the firewall hole, but you're not sleeping easy,
so you go back to your perimeter notes and look harder. And you catch
it — the thing underneath the thing.

There's an internal service on this box — a diagnostics endpoint, the
kind of thing meant only for the machine to talk to itself — and it's
bound to `0.0.0.0`. In plain terms: it's listening on EVERY network
interface, including the one that faces the world, when it should only
ever answer to `127.0.0.1`, the box's own private loopback. The
firewall was the only thing hiding it, and firewalls fail, get
misconfigured, get reloaded wrong at 3 AM. Defense in depth means the
service itself shouldn't be exposed in the first place.

This is the difference between a pro and an amateur on defense: the
amateur trusts one wall. The pro assumes every wall fails and makes
sure the thing behind it is safe anyway. GREERSON bound everything to
`0.0.0.0` because it "just worked" — the two most expensive words in
this business.

Find the service's config (under /etc/), change its bind address from
`0.0.0.0` to `127.0.0.1` so it only answers to the local machine, and
restart it. Then prove it with `ss` — it should now be listening on
127.0.0.1, not the whole world.
```

**Objectives:**
- Locate the service config binding to `0.0.0.0`
- Change the bind/listen address to `127.0.0.1` (loopback only)
- Restart the service and confirm via `ss -tlnp` that it now binds to 127.0.0.1

**Victory text:**
```
`127.0.0.1:<port>` — there in the `ss` output, exactly where it
belongs. The diagnostics endpoint answers to the box and to no one
else now, its ear turned inward, deaf to the street. Even if the
firewall falls tomorrow — misconfigured, reloaded wrong, disabled by
some future tired hand — this door no longer opens outward at all.
There's nothing behind it for the Ferryman to reach.

That's defense in depth, and it's the whole philosophy of blue-team
work in one config change: never rely on a single control. The
firewall is a wall; binding to loopback is making sure the treasure
isn't sitting against the wall in the first place. Layers. Always
layers. The Ferryman only has to be right once — so you have to be
right in depth, so that his one right answer still isn't enough.

The wall is high now. The doors face inward. And somewhere in the logs
you haven't read yet, a patient man is not remotely worried.  (+160)
```

**Hints:**
1. "From your `ss -tlnp` output, find the service whose local address is `0.0.0.0:<port>` (all interfaces). Then find its config file under `/etc/` — search for `0.0.0.0` (`sudo grep -rn '0.0.0.0' /etc/<service>/`)."
2. "Change the bind/listen/host directive from `0.0.0.0` to `127.0.0.1`, save, and restart the service: `sudo systemctl restart <service>`."
3. "Edit the config's bind address to `127.0.0.1`, `sudo systemctl restart <service>`, verify with `sudo ss -tlnp` (should show `127.0.0.1:<port>`), then `check`."

---

### t4_l4 — Building the Wall

**Intro:**
```
2:30 AM. Patchwork's not enough anymore. You've been closing individual
holes like a man plugging leaks with his fingers, and the Ferryman has
more patience than you have fingers. Time to stop reacting and set a
policy: default-deny. The oldest, hardest rule in security — everything
is forbidden unless explicitly allowed.

Right now this box's firewall runs the friendly way GREERSON left it:
mostly open, blocking a few known-bad things, trusting the rest. That's
backwards. A fortress doesn't list the people who AREN'T allowed in —
it lists the few who are, and turns everyone else away at the gate by
default. You're going to flip the whole posture.

Two moves with `firewall-cmd`:
  - Set the default zone to `drop` — the zone that silently discards
    anything you didn't explicitly permit. The gate says no unless told
    otherwise.
  - Then explicitly allow ONLY what this box legitimately needs to face
    the world: SSH (so you can get in) and the web service (its actual
    job). Nothing else. Permanent, then reload.

Miss the SSH rule and you lock yourself out of your own fortress — so
read twice, allow ssh, THEN flip to drop. Build the wall. Leave exactly
two doors, both guarded, both yours.
```

**Objectives:**
- Ensure SSH and the web service (http/https) are explicitly allowed
- Set the default firewalld zone to `drop` (default-deny posture)
- Make it permanent, reload, and confirm only the intended services are allowed

**Victory text:**
```
`--list-all` on the drop zone: ssh, http, https, and a great
disciplined silence where everything else used to be welcome. The wall
is up and its logic is finally correct — not "keep out the bad" but
"let in only the known," which is the only posture that works against
someone whose whole craft is being the threat you didn't list.

You flipped a machine from trusting-by-default to denying-by-default
without locking yourself out — you allowed your own SSH key through the
gate before you closed it, because you read twice and acted once. That
sequence, that discipline, is the difference between hardening a box and
bricking it. GREERSON ran default-allow for a decade and called the
quiet "secure." It wasn't secure. It was just quiet. There's a
difference, and the Ferryman lives in it.

The fortress is real now. High walls, two guarded doors, a default of
NO. You should feel safe.

You don't. Why don't you?                                    (+180)
```

**Hints:**
1. "First, guarantee your way in and the box's job are allowed: `sudo firewall-cmd --permanent --add-service=ssh`, `--add-service=http`, `--add-service=https`. Do this BEFORE changing the default zone or you risk locking yourself out."
2. "Set default-deny: `sudo firewall-cmd --set-default-zone=drop`. The drop zone discards everything not explicitly allowed. Then make permanent rules live with `sudo firewall-cmd --reload`."
3. "Add ssh/http/https as permanent services, `sudo firewall-cmd --set-default-zone=drop`, `sudo firewall-cmd --reload`, confirm with `sudo firewall-cmd --list-all`, then `check`."

---

### t4_l5 — The Front Door

**Intro:**
```
4:05 AM. Last thing on the fence line, and it's the big one: the front
door itself. SSH. The one way in you deliberately left open — which
makes it the one door the Ferryman has been leaning on hardest.

You finally read the SSH logs properly, and your stomach drops. On a
RHEL box the record lives in `/var/log/secure`, and it's a wall of
them: failed login after failed login, thousands, from addresses all
over the map, hammering at accounts — root, admin, and yes, root again,
ten times a second, for weeks. Someone has been brute-forcing the front
door of this machine since before you started, and GREERSON left that
door configured about as securely as a screen with the latch off:

  - Root can log in directly over SSH — so every one of those thousands
    of guesses is aimed straight at the keys to the kingdom.
  - Password authentication is on — so the door can be opened by anyone
    who guesses right, no key required, just patience. And patience is
    the Ferryman's entire religion.

You're going to change the locks. Edit `/etc/ssh/sshd_config`:
  - Set `PermitRootLogin no` — nobody rides straight to root.
  - Set `PasswordAuthentication no` — keys only, from here on. Guessing
    stops working entirely. (Your key's already installed — you did that
    in the prologue. Past-you was looking out for present-you.)

Validate the config with `sshd -t` before you trust it, restart sshd,
and shut the brute-force down for good.
```

**Objectives:**
- In `/etc/ssh/sshd_config`, set `PermitRootLogin no` and `PasswordAuthentication no`
- Validate the config syntax (`sshd -t`)
- Restart `sshd` and confirm the settings are active

**Victory text:**
```
`sshd -t` returns silent and clean; the restart takes; and just like
that, the thousands of nightly guesses hammering `/var/log/secure`
become noise against a door that no longer opens for guesses at all.
Root can't be reached from outside. Passwords don't work anymore. The
only way through the front door now is a key you hold — and the Ferryman
doesn't have it.

This is the highest-value fifteen minutes in practical security, and
GREERSON never spent them. Disabling direct root login and password
auth over SSH shuts down the overwhelming majority of real-world
intrusions — not with anything clever, just with two lines in a config
file and the discipline to validate before you reload. Keys, not
guesses. No express lane to root. You changed the locks on the one door
you had to leave standing.

The brute-force stops. The log goes quiet.

And that's when the cold really hits you — because a professional
stopped throwing himself at this door a long time ago. The failed
logins are old. The recent logs are clean. Too clean.

He stopped knocking because he stopped needing to. He's not outside
your wall.

He's been inside it for weeks.                               (+200)

                              [ TIER 4 CLEARED — badge earned ]
```

**Hints:**
1. "Read the evidence first: `sudo grep 'Failed password' /var/log/secure | tail`. Then edit `sudo vi /etc/ssh/sshd_config` — find `PermitRootLogin` and `PasswordAuthentication` (uncomment if needed)."
2. "Set `PermitRootLogin no` and `PasswordAuthentication no`. Before restarting, validate syntax: `sudo sshd -t` (no output = good). Never restart sshd on an unvalidated config."
3. "Set both directives to `no`, run `sudo sshd -t`, then `sudo systemctl restart sshd`; confirm with `sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication'`, then `check`."

---

## Closing Beat (end of Tier 4, turn toward Tier 5)

```
You stand up too fast. The chair rolls back and hits the rack behind
you and the whole aisle of machines answers with their cold indifferent
hum, and for the first time in four nights the sound doesn't comfort
you. Because if he's already inside, then some of that humming is him.

You built a beautiful wall tonight. Default-deny, loopback bindings,
keys-only SSH, every window bricked and every door guarded. It's real
work, good work, the best on this box in a decade. And it is, you
realize with the specific nausea of a lesson learned too late, a wall
built around a man who's already sitting in your living room.

You go back through the logs with different eyes — not looking for who's
knocking anymore, but for who already answered. And there, buried in a
directory you had no reason to open, is a single file that isn't yours,
isn't GREERSON's, isn't the system's. A plain text file. One line,
lowercase, unhurried:

    // ferryman was here. thanks for the heartbeat, kid.
       greerson always did leave a light on. — f

He knows your name. He read the notes. He's been watching you patch
holes all week from somewhere inside the very machine you were fortifying,
and he left this where he knew you'd eventually look, because a man that
patient enjoys the moment you finally understand.

The wall is finished. The enemy is home.

Tomorrow night you stop defending the perimeter and start hunting the
thing inside it. You find every trace he left, every door he cut, every
piece of himself he wired into your box to keep his way back in — and
you tear it out by the roots until this machine is yours again and his
not at all.

The pager is silent. The Ferryman is patient.

Neither one of those is your friend.

                                        [ Tier 5 awaits ]
```

---

## TIER 5 — "Incident Response & Security"

> The fifth and final shift. No more accidents, no more perimeter drills. There is a professional living inside your machine, and tonight is the hunt: find every trace, pull every root, and evict him for good. This is the campaign's climax and its exam — every skill from four nights converges into one long, cold, methodical eviction. Blue team, full contact.

### Tier 5 — Opening beat

```
7:58 PM. You came in early. Couldn't not.

You've spent the daylight hours — the ones normal people use for
sleeping — reading everything you could find about how a professional
lives inside a machine he's stolen. And the thing that scared you most
wasn't the cleverness. It was the patience. A good intruder doesn't
trash the place. He moves in quietly, makes himself a set of keys, hides
a few ways back inside, and waits. He becomes part of the furniture.
He counts on you being too busy fighting fires to notice the smell of
someone else's cigarette in your own house.

The Ferryman has been furniture for weeks.

Tonight you evict him, and there's a right order to it — the incident
responder's discipline, learned hard by everyone who ever learned it:
  1. Find how he got in and what he touched. (Footprints.)
  2. Find the accounts he made himself. (Identity.)
  3. Find the automation he left to let himself back in. (Persistence.)
  4. Find what he's running right now. (The live threat.)
  5. Change every lock so nothing he holds still opens. (Eviction.)

You don't get to skip steps. Skip the footprints and you'll miss a door.
Kill the process before you've found the persistence and it just respawns
at midnight. Slow is smooth. Smooth gets him out and keeps him out.

Pour the coffee. Turn on every light in the house.

Let's find out who's been living in your walls.

                              [ Tier 5, Level 1 unlocked ]
```

---

### t5_l1 — Footprints

**Intro:**
```
You start where every real investigation starts: the logs. Not to fix
anything yet — just to learn the truth of what happened here, because
you can't evict a man whose movements you don't understand.

The story of who came and went on a RHEL box is written in a few
specific places, and tonight you're going to read them like a detective
reads a room:
  - `/var/log/secure` — every authentication event: SSH logins, sudo
    use, successes AND failures. This is the front-door camera.
  - `last` — reads the login record (wtmp): every successful session,
    who from where and for how long.
  - `lastb` — reads the FAILED login record (btmp): every rejected
    attempt. The brute-force you already saw lives here.

The brute-force was noise — thousands of failures, all rejected. What
you're hunting for is the needle: the ONE login that shouldn't have
worked and did. A successful SSH session from an outside address you
don't recognize, at an hour no employee keeps, from an account that
shouldn't be logging in remotely at all. That's the Ferryman's first
footprint — the moment furniture became a person.

Find the intruder's successful login in the logs. Identify the source
IP address he came in from, and write it into /root/incident/attacker_ip.txt.
Name the ghost. Everything else tonight hangs off knowing where he
entered.
```

**Objectives:**
- Examine `/var/log/secure`, `last`, and `lastb` to distinguish failed brute-force from the successful intrusion
- Identify the attacker's source IP from the anomalous successful login
- Record it in `/root/incident/attacker_ip.txt`

**Victory text:**
```
`/root/incident/attacker_ip.txt` — one address, and the whole night
snaps into focus around it. That's the door he walked through. Not
guessed at, not assumed: found, in the box's own honest record of
everyone who ever knocked and everyone who ever got in. You separated
the roar of ten thousand failures from the single quiet success that
mattered, which is the entire art of log analysis — signal pulled
living from noise.

This is where incident response actually begins: not with panic, not
with pulling cables, but with evidence. You know when he came in now.
You know from where. Every trace you find for the rest of the night,
you can line up against that timestamp and that address and ask the
only question that matters — *is this him?* GREERSON left a diary of
accidents. The Ferryman tried to leave nothing. But nobody walks
through a logged door without the log remembering.

He remembers now. So do you. Follow the footprints in.       (+160)
```

**Hints:**
1. "Failed attempts: `sudo lastb | head`. Successful logins: `last | head`. Cross-reference against `/var/log/secure`: `sudo grep 'Accepted' /var/log/secure` shows successful SSH logins (vs 'Failed password' for the brute-force noise)."
2. "Look for an `Accepted` login from an unfamiliar IP at an odd hour — that's the intrusion. The source IP is in that log line. Create the incident dir: `sudo mkdir -p /root/incident`."
3. "Find the anomalous accepted login (`sudo grep 'Accepted' /var/log/secure`), then record the source IP: `echo '<IP>' | sudo tee /root/incident/attacker_ip.txt`. Then `check`."

---

### t5_l2 — The Locksmith's Ghost

**Intro:**
```
10:30 PM. You know how he got in. Now you find what he MADE while he was
here — because the first thing a professional does inside a stolen box
is stop needing the way he came in. He builds himself his own key.

There are two classic moves and the Ferryman, being thorough, may have
made both:
  - A new user account, quietly added, that looks boring on purpose —
    a name like 'systemd-bus' or 'ftpuser', something your eye slides
    right off. Worse: an account with UID 0, which on Linux means it IS
    root, no matter what it's called. A second root by another name.
  - A legitimate-looking account slipped into the `wheel` group — the
    group that grants sudo on a RHEL box — so an innocuous user can
    quietly become root whenever he likes.

The account database is `/etc/passwd`, and it cannot hide from you if
you know how to ask:
  - Every account with UID 0 is root-equivalent. There should be exactly
    ONE. If there are two, the second one is a backdoor wearing a name
    tag.
  - `getent group wheel` lists everyone who can sudo. Anyone there who
    shouldn't be is a key the Ferryman cut for himself.

Audit the accounts. Find the identity he built — the rogue root-
equivalent user and/or the unauthorized wheel member. Lock it down: at
minimum lock the account and strip its sudo, or remove it outright.
Then confirm there's exactly one UID-0 account again, and it's the real
root.
```

**Objectives:**
- Audit `/etc/passwd` for UID 0 accounts and `wheel` group membership
- Identify the rogue account(s) the attacker created / escalated
- Lock or remove the backdoor account and revoke unauthorized sudo access
- Confirm only legitimate root/wheel access remains

**Victory text:**
```
One UID 0 again. One root, the real one, standing alone in
`/etc/passwd` the way it always should have. The `wheel` group trimmed
back to the names that earned their place. The key the Ferryman cut for
himself — the quiet little account he was so proud of, boring by design
— locked, stripped, and gone. He can't become root through the front of
the house anymore.

This is the audit that saves companies, and almost nobody runs it until
after it's too late: *who, on this machine, can become root, and do I
recognize every single one of them?* An attacker's whole game is
turning one moment of access into permanent power, and permanent power
on Linux means UID 0 or a seat in wheel. You just counted the thrones
and threw out the pretender. GREERSON never audited his users once —
that's half why the Ferryman had room to work.

One identity down. But a careful man never keeps just one key.  (+180)
```

**Hints:**
1. "Find all root-equivalent (UID 0) accounts: `awk -F: '($3==0){print $1}' /etc/passwd` — there should be only `root`. List sudoers: `getent group wheel`. Also scan for recently added users at the bottom of `/etc/passwd`."
2. "Lock a rogue account: `sudo usermod -L <user>` and `sudo usermod -s /sbin/nologin <user>`, or remove it entirely: `sudo userdel -r <user>`. Remove someone from wheel: `sudo gpasswd -d <user> wheel`."
3. "Identify the extra UID-0 or unauthorized wheel user, then `sudo userdel -r <user>` (or lock + `sudo gpasswd -d <user> wheel`). Confirm with `awk -F: '($3==0){print $1}' /etc/passwd` (only root) and `getent group wheel`, then `check`."

---

### t5_l3 — The Thing That Waits for Midnight

**Intro:**
```
12:40 AM. You've taken his keys. If the Ferryman is who you think he is,
he already assumed you would — and left something that doesn't need a
key at all. Persistence: automation he planted so the box itself invites
him back in, on a schedule, without him lifting a finger.

You learned in Tier 3 how the living things on this box get scheduled
and started. Now you turn that knowledge adversarial, because every
mechanism that keeps a good service alive can keep a bad one alive just
as well:
  - `cron` — the classic. A job in `/etc/cron.d/`, `/etc/crontab`, or a
    user's `crontab -l`, set to phone home or reopen a shell every few
    minutes. Look for entries that curl a strange address, pipe to bash,
    or run a script out of /tmp or /dev/shm.
  - A malicious **systemd unit** — a service or timer with an innocent
    name doing guilty work, the grown-up version of the same trick.
    (You've masked one suspicious timer already this campaign. This one
    isn't a heartbeat.)

Hunt the persistence. Check the cron directories and every user's
crontab; list the timers and units for anything that doesn't belong,
anything pointing at that attacker IP or running code from a temp
directory. When you find the Ferryman's callback, kill its schedule at
the root: remove the cron entry, and stop/disable/mask the rogue unit
so it can never fire again.
```

**Objectives:**
- Inspect cron (`/etc/cron.d/`, `/etc/crontab`, user crontabs) and systemd units/timers for malicious persistence
- Identify the attacker's callback/backdoor mechanism (often referencing the attacker IP or /tmp, /dev/shm)
- Remove the cron entry and/or stop-disable-mask the rogue unit so it cannot re-trigger

**Victory text:**
```
The schedule is broken. Whatever the Ferryman wired to wake up every
few minutes and quietly reach across the river to let him back in —
it's gone from cron, or masked dead in systemd, and it will not fire
tonight or any night. You didn't just delete a file; you understood the
MECHANISM, found where a repeating thing was told to repeat, and cut it
out at the schedule.

This is the step people skip and regret. They find the malware, they
kill the process, they high-five, they go home — and at 12:45 the cron
job runs and the whole nightmare respawns, because they treated a
symptom and left the heartbeat of the infection beating. Persistence is
what turns a breach into a haunting. You went looking for the thing that
WAITS, and you found it, because four nights ago a dying man taught you
— without meaning to — exactly how a scheduled thing hides in plain
sight.

The Ferryman's automatic door is bricked. Now for the one he's holding
open by hand.                                                (+190)
```

**Hints:**
1. "Check cron: `sudo ls -la /etc/cron.d/ /etc/cron.*`, `sudo cat /etc/crontab`, and each user's jobs `sudo crontab -l -u <user>`. Check systemd: `systemctl list-timers --all` and `systemctl list-units --type=service`. Look for anything referencing the attacker IP, /tmp, /dev/shm, or piping to bash."
2. "Remove a malicious cron file: `sudo rm /etc/cron.d/<file>` (or edit the crontab to delete the line). Neutralize a rogue unit: `sudo systemctl stop <unit> && sudo systemctl disable <unit> && sudo systemctl mask <unit>`."
3. "Delete the attacker's cron entry and/or stop-disable-mask the rogue unit, verify it's gone from `systemctl list-timers --all` / cron dirs, then `check`."

---

### t5_l4 — What He's Running Right Now

**Intro:**
```
2:50 AM. Keys taken, schedule broken. The Ferryman's automated ways back
in are dead. Which leaves the thing he's got running RIGHT NOW — the
live connection, the process he's using as you read this, the reason the
back of your neck has been cold all week.

Somewhere in the process table is a listener that isn't yours: a
backdoor, maybe a reverse shell, a program sitting quietly with a socket
open, waiting for or actively holding a connection to that attacker IP.
This is where the whole campaign's toolkit converges — network sight and
process sight, used together like a hunter using both eyes:
  - `ss -tnp` shows ESTABLISHED connections and the process behind each.
    An active connection to the attacker's IP is him, live, on the wire.
  - `ss -tlnp` shows what's LISTENING — a backdoor waiting for him to
    call in sits here, on some port that was never in your inventory.
  - From the socket you get a PID; from the PID you get everything —
    `ls -l /proc/<PID>/exe` reveals the actual binary behind it, usually
    lurking somewhere it has no business being: /tmp, /dev/shm, a dotfile
    dir.

Find the live backdoor. Trace the connection or the rogue listener to
its PID, follow the PID to the malicious binary on disk. Then end it
properly — kill the process, and remove the binary so it can't be
relaunched. Cut the hand he's holding the door open with.
```

**Objectives:**
- Identify the malicious live connection or backdoor listener (`ss -tnp` / `ss -tlnp`)
- Trace it to its PID and locate the backing binary (`ls -l /proc/<PID>/exe`)
- Kill the process and remove the malicious binary from disk
- Confirm no connection to the attacker IP and no rogue listener remains

**Victory text:**
```
Dead. The process gone from the table, its socket closed, the binary
that backed it wiped off the disk it was squatting on. You put your two
kinds of sight together — the network's and the system's — walked a live
socket back to a PID, walked the PID back to a file hiding in /tmp like
every piece of malware since the dawn of /tmp, and you ended both the
process and the thing on disk that could relaunch it. No connection to
his address anywhere in `ss` now. No listener you didn't put there.

That's the convergence this whole game was built toward: `ss` to see the
wire, `ps` and `/proc` to see the machine, and the instinct to follow a
thread from one into the other until it ends at a file you can delete.
An attacker's live foothold always touches both worlds — a process and a
port — and a real defender can read both. You just did, cold, at three in
the morning, and pulled his hand out of your door.

The Ferryman is running nothing on this box now. But somewhere out there
he still holds one last key — the one you gave every intruder the moment
you inherited GREERSON's box.                                (+200)
```

**Hints:**
1. "Live connections: `sudo ss -tnp` — look for an ESTABLISHED connection to the attacker IP from t5_l1. Backdoor listeners: `sudo ss -tlnp` — any port not in your legitimate inventory. Both give you a PID in the process column."
2. "Trace the PID to its binary: `sudo ls -l /proc/<PID>/exe` (shows the real path, often in /tmp or /dev/shm). Kill it: `sudo kill -9 <PID>`. Then remove the binary: `sudo rm -f <path>`."
3. "Find the rogue socket (`sudo ss -tnp`/`-tlnp`), trace with `sudo ls -l /proc/<PID>/exe`, `sudo kill -9 <PID>`, `sudo rm -f <binary>`, confirm it's gone from `ss`, then `check`."

---

### t5_l5 — Changing the Locks

**Intro:**
```
4:30 AM. He's out. No account, no cron, no unit, no process, no listener.
For the first time in weeks the Ferryman is running nothing and holding
nothing on this machine.

Except.

A professional always keeps one quiet way back, the one amateurs forget
to look for because it isn't a program or an account — it's a KEY. The
very first thing you did on this box, back in the prologue, was install
an SSH key so you'd never need a password again. The Ferryman read that
playbook too. If he dropped his own public key into an `authorized_keys`
file anywhere on this system, then every wall you built tonight is
theater: he can walk through the hardened front door as a trusted guest,
no password, no brute-force, welcomed by name, whenever he wants.

This is the last lock, and it's the one that matters most:
  - Check `authorized_keys` for every account that has one — root,
    student, any service account, especially any user he created before
    you deleted it. `/root/.ssh/authorized_keys`, `/home/*/.ssh/authorized_keys`.
  - Every key in those files should be one YOU recognize. Yours. Any key
    you can't account for is his, and it has to come out.

Find the Ferryman's key. Remove it from every authorized_keys file it
poisoned. Leave only keys you trust. Then — the responder's final act —
confirm the door only opens for you. Change the last lock. Take your
house back.
```

**Objectives:**
- Inspect `authorized_keys` for all accounts (`/root/.ssh/`, `/home/*/.ssh/`)
- Identify and remove the attacker's unauthorized public key(s)
- Ensure only trusted (your own) keys remain
- Confirm the box no longer trusts any attacker-controlled credential

**Victory text:**
```
The last key turns. You comb every `authorized_keys` file on the box —
root's, student's, the ghosts of accounts you already deleted — and you
find it, of course you do, sitting in root's own trusted-keys file like
he owned the place: one public key that was never yours. You cut it out.
You read what's left. Every remaining key is one you can name. The door
opens for you and for no one else alive.

And that's the eviction complete — done in the only order that ever
works. Footprints, identity, persistence, live threat, credentials. You
didn't panic and pull the plug. You didn't kill one process and call it
a win. You investigated, you understood, and you removed him root and
branch, in sequence, until there was nothing of the Ferryman left in the
machine but the memory of how close it was.

You lean back. 5:00 AM. The racks hum — just the racks now, nothing
hiding in the sound. The box is yours. Actually, wholly yours, for the
first time since you walked in five nights ago and found a stranger's
misspelled name tag on the desk.

Then you do the last thing. You open the masked heartbeat timer — the
one from Tier 3, the one that started all of this, GREERSON's love
letter that the Ferryman read as an address. You don't delete it. You'll
never delete it. But you rewrite where it points: no more signal across
the river to a hospital room that's empty now. Just a quiet local line,
written to a log only you read, once a night, at 3:33 AM.

    box is still alive. — the kid

Somebody should know. Even if it's only you.

                              [ TIER 5 CLEARED — FINAL BADGE EARNED ]
```

**Hints:**
1. "Check every authorized_keys file: `sudo cat /root/.ssh/authorized_keys` and `sudo cat /home/*/.ssh/authorized_keys`. Each line is one public key with a comment at the end — you're looking for one that isn't yours."
2. "Remove the attacker's key line from the file (edit with `sudo vi`, delete that line). Keep only keys you recognize. Verify file permissions are still tight (`600`, owned by the account)."
3. "Delete the unauthorized key line from each poisoned `authorized_keys`, confirm only your key remains (`sudo cat` each file), then `check`."

---

## FINALE — "Sunrise, Fourteenth Floor"

```
5:41 AM. Five nights.

The sun comes up over the parking lot the way it always does — grey,
cheap, indifferent, the color of a monitor left on too long. You've
watched it do this five mornings running now, and somewhere in there it
stopped being an enemy. It's just the sun. It doesn't care about the
box. That was never its job. Caring about the box turned out to be
yours.

You take inventory, the good kind, the kind GREERSON never ran. You know
where everything is now, because you found it in the dark. You know who's
allowed to touch it, because you set the locks yourself. You know what's
running and what's dying, what faces the street and what faces inward,
and you know — bone-deep, the way you only learn by doing it at 3 AM with
your hands shaking — how to throw a stranger out of a house he thought
was his.

Two ghosts haunted this machine when you inherited it. GREERSON, who
loved it too much to secure it, and left it wounded and broadcasting.
The Ferryman, who loved nothing, and followed the wound in. One taught
you the cost of caring without discipline. The other taught you the cost
of discipline without care. Somewhere between those two men is the job.
Somewhere between those two men is you.

The desk is yours now. You should fix the tape with your name on it.

You don't. You leave it misspelled. It's yours misspelled. It's part of
the place.

The pager sits quiet on the desk, for now. It won't last — it never does,
that's the whole nature of the thing. Somewhere a service will die, a
disk will fill, a stranger will start knocking. That's not a tragedy
anymore. That's just the next shift.

You pour one more cup of the terrible coffee and pull up a chair that's
finally, entirely yours.

You're the senior admin now.

Try to leave better notes than the last one did.

                    ┌─────────────────────────────────┐
                    │   SYSADMIN ZORK                  │
                    │   Night Shift — Complete         │
                    │                                  │
                    │   Tiers cleared ........ 5 / 5   │
                    │   The box is yours.              │
                    └─────────────────────────────────┘

                                        [ ROLL CREDITS ]
```
