#!/bin/zsh
# P2 preflight: one real org-agent run in an arm (protocol 9). Usage: preflight_run.sh <R|C>
# A throwaway org under /tmp/hirearchy-p2/ (the arm's CLI: init, hire root lead, task root lead), one scheduler run
# (`hirearchy --root <org> run --until-done`, KIRO_HOME unset), then model_check.sh org on its run logs: every `# cmd:` carries
# `--model claude-sonnet-5.5` and `--effort high`. Output into EV/preflight/preflight-<arm>/. It costs one org run.
ARM_IN="$1"; H0=${0:A:h}
source $H0/arm.sh preflight-$ARM_IN || exit 2
[[ -z "${KIRO_HOME+set}" ]] || { echo "REFUSED: KIRO_HOME is set" >&2; exit 3; }
D=$EV/preflight/preflight-$ARM; mkdir -p $D; S=$P/preflight-$ARM-$(date +%s); mkdir -p $S; echo $S > $D/sandbox-path.txt
{
  "${HIR[@]}" init $S/org --mission "Preflight."; echo "init exit $?"
  "${HIR[@]}" --root $S/org hire root lead --role "Writer" --charter "Answers one question per task in one line."; echo "hire exit $?"
  "${HIR[@]}" --root $S/org task lead --title "Say hello" --goal "Reply with the word hello." --acceptance "The reply is hello." --budget 2; echo "task exit $?"
  "${HIR[@]}" --root $S/org run --until-done --max-runs 2; echo "run exit $?"
} > $D/run.txt 2>&1
zsh $H0/model_check.sh org preflight-$ARM $S | tail -3
grep -h '^# cmd:' $(find $S/org -path '*/runs/*.log') 2>/dev/null | head -3 >> $D/run.txt
echo "preflight run arm $ARM: $(grep -c -- '--effort high' $D/run.txt) '# cmd:' line(s) with --effort high (see $D/run.txt)"
