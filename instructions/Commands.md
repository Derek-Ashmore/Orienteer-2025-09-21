# Command templates

> Command prompt base
```
npx claude-flow swarm "" --claude
```

> 12 Factor Analysis instruction
```
npx claude-flow swarm "Perform a twelve-factor analysis on this application and put the results in folder 12-factor. twelve-factor principles are documented at https://www.12factor.net/  I want to know where this application falls short of twelve-factor principles so that I can assess it's ability to capitalize on public cloud dynamic scaling and avilability features should it be deployed there. Do not change the application yet. I'm only interested in the twelve-factor analysis. Please let me know if you need additional information." --claude
```

> Reverse Engineer Requirements instruction
```
npx claude-flow swarm "Reverse engineer the business requirements for this application and put the results in folder requirements. The documented requirements should be in enough detail that you could rewrite the application using other technology choices or programming languages. Additionally, any rewrite would likely be hosted in a public cloud. Please let me know if you need additional information." --claude
```