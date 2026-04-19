theres two folders, one called skills-python. this is a collection of claude code skills
installation: clone the repo. tell your claude code to install the skills at the path. it will add it to the .claude.json or whaever. then restart your session/start a fresh session and start querying cluade. 

codex-plugin-python. this is a codex plugin. 
installation clone the repo. tell codex to add this plugin from a local path. then start a fresh session. you should see the plugin in /plugins and then 

differences: the two implementations are mostly identical, except codex plugin has extra plugin metadata (plugin.json, someone should edit this at some point (not me)). also codex recommended me tirm the skill.md and put extra information in an api.md (the skill-creator skill in codex said this)

expected behavior: when you ask your agent to do a boltz relevant task “fold a protein”, it will
read the right skill.md
estimate the cost (enforced via the skill.md)
ask you if you want to proceed? (it would be nice if we can build this into the cc/codex permission ui but idt theres a way to do this)
then run it. it takes care of polling and downloads the structure/metadata etc. 