# Rules Files

This directory contains JSON rules files for the Rules Evaluator tool.

## File Structure

Each JSON file should follow this structure:

```json
{
  "prompts": [
    {
      "prompt": "Your prompt text",
      "rules": [
        {
          "ruletype": "critical|important|expected|desirable",
          "ruledescription": "Description of what the response must/should contain"
        }
      ]
    }
  ]
}
```

## Rule Types

- **critical**: Must have - if this fails, the entire prompt fails (score: 0)
- **important**: Really needed - worth 50% of non-critical points
- **expected**: Should be present - worth 35% of non-critical points  
- **desirable**: Nice to have - worth 15% of non-critical points

## Examples

See `example_rules.json` for a complete example.

## Best Practices

1. Keep rule descriptions clear and specific
2. Use critical rules sparingly - only for absolute requirements
3. Order rules by importance for readability
4. Test your rules with sample content before full evaluation
5. Name files descriptively (e.g., `customer_service_rules.json`, `product_info_rules.json`)