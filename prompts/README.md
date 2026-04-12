# Sample Prompts

Testsmith ships with a solid default system prompt that enforces quality rules
(deterministic expected results, no vague language, uniqueness checks, etc.).

For more control, use these sample prompts as starting points via `-s` and `-u`:

```bash
# Use a sample system prompt (replaces the default persona, keeps output contract)
testsmith -s @prompts/system_advanced.md -p "Login with email and password"

# Use a sample system prompt in append mode (adds to the default)
testsmith -s @prompts/system_mobile_app.md --append-system -p "Login screen"

# Combine system + user template
testsmith -s @prompts/system_advanced.md -u @prompts/user_with_checklist.md -f spec.pdf
```

## Files

| File | Use with | Description |
|------|----------|-------------|
| `system_advanced.md` | `-s @prompts/system_advanced.md` | Full-featured prompt with phased execution model, priority distribution targets, and language lint self-check. Best for maximizing quality from large PRDs. |
| `system_mobile_app.md` | `-s @prompts/system_mobile_app.md --append-system` | Add-on modules for mobile app testing: Dark Mode, Accessibility, platform-specific checks. Best used with `--append-system`. |
| `user_with_checklist.md` | `-u @prompts/user_with_checklist.md` | User prompt template that asks the LLM to extract a checklist before generating tests. Improves coverage for complex specs. Works standalone or paired with `system_advanced.md`. |

## Customizing

1. Copy a sample prompt and modify it for your needs.
2. Domain-specific rules (document authority, conditional modules) belong in
   your custom prompts, not in the default.
3. The built-in output contract (JSON schema, field quality rules, self-check)
   is always appended — even when you use `-s` to replace the system prompt.
   You don't need to repeat those rules in your custom prompt.
4. Use `--append-system` when you want to add instructions on top of the
   default. Use `-s` alone when you want full control over the persona.
