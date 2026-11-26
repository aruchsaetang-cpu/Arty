#!/usr/bin/env bash
# Waits for run_to_end.done, then puts the finished film on GitHub (branch claude/install-agent-tools-kwf2l7) so it can be downloaded without Claude.
cd "$(dirname "$0")/../.."
while [ ! -f shorts/aura/run_to_end.done ]; do sleep 120; done
F=shorts/aura/out/aura_monster.mp4
if [ "$(stat -c %s $F)" -gt 95000000 ]; then ffmpeg -v error -y -i $F -c:v libx264 -crf 24 -preset slow -c:a copy shorts/aura/out/aura_monster_small.mp4 && F=shorts/aura/out/aura_monster_small.mp4; fi
git add -f "$F" && git commit -qm "Finished film (rendered unattended)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RmZcNKw4UE8v1k2Jyijr8e" && git push -q -u origin claude/install-agent-tools-kwf2l7 && echo "$(date +%H:%M) film pushed: $F" > shorts/aura/after_done.log
