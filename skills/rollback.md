# skill: rollback
## 执行步骤
1. 显示最近 10 次 git commit：
exec: cd ${WORKSPACE} && git log --oneline -10

2. 输出列表，请主人指定回滚目标（commit hash）

3. 主人确认后，执行软回滚（生成新 commit，不破坏历史）：
exec: cd ${WORKSPACE} && git revert <hash> --no-edit

4. 执行健康检查：
exec: bash ${WORKSPACE}/scripts/health-check.sh

5. 写入回滚事件到 events.jsonl：
{"ts":"ISO时间","type":"rollback","uuid":"uuidv4","session_id":"xxx","target_commit":"hash","reason":"原因"}

6. 输出回滚结果摘要
