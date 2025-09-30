# Command templates

> Command prompt base
```
npx claude-flow@latest swarm "" --claude
```

> 12 Factor Analysis instruction
```
npx claude-flow@latest swarm "Perform a twelve-factor analysis on this application and put the results in folder 12-factor. twelve-factor principles are documented at https://www.12factor.net/  I want to know where this application falls short of twelve-factor principles so that I can assess it's ability to capitalize on public cloud dynamic scaling and avilability features should it be deployed there. Do not change the application yet. I'm only interested in the twelve-factor analysis. Please let me know if you need additional information." --claude
```

> Reverse Engineer Requirements instruction
```
npx claude-flow@latest swarm "Reverse engineer the business requirements for this application and put the results in folder requirements. The documented requirements should be in enough detail that you could rewrite the application using other technology choices or programming languages. Additionally, any rewrite would likely be hosted in a public cloud. Please let me know if you need additional information." --claude
```

> Product Migration analysis instruction
```
npx claude-flow@latest swarm "My intention is to replace an installation of this product at an enterprise with a SaaS product alternative. Do a market analysis to determine which SaaS products would be the best candidates for migration. Place the analysis in folder product-migration-analysis/market-analysis. Product selection will be based on preserving end-user capabilities to the extent possible and an estimate of the migration effort. Please let me know if you need additional information." --claude
```

> Salesforce Migration planning instruction
```
npx claude-flow@latest swarm "Plan a migration an installation of this product to Salesforce. I wish to automate the migration as much as possible so that repeated test migrations are possible. Don't change the application or write migration automation yet. I'm interested in the plan to create and execute the migration. Place the analysis in folder product-migration-analysis/salesforce-migration. Please let me know if you need additional information." --claude
```