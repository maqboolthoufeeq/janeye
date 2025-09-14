# Bash commands

- npm run build: Build the project
- npm run type-check: Run the typechecker
- pre-commit run --all: to format the repo

# Code style

- Use Tailwind and HTML
- Use Hooks to wrap api request and save the response.data in cache Zustand
- I prefer use small file like max 300 lines of code
- Refactor in smaller components huge file

# Workflow

- Be sure to typecheck and pre-commit when you’re done making a series of code changes
- Be sure to don't make twice the api requests caused often by rerenders

# Note

- Don't run npm run build, but run npm run pre-commit
