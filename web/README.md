# JanEye Web - Next.js Application

A modern Next.js application for JanEye's platform, built with TypeScript, Tailwind CSS, and following Next.js best practices.

## 🎨 Design System

### Brand Colors

- **Primary**: `#4F46E5` (Indigo) - Innovation and technology
- **Secondary**: `#10B981` (Emerald) - Efficiency and growth

### Typography

- **Font**: Inter from Google Fonts
- Optimized for readability and modern design

## 🚀 Features

- ⚡ **Next.js 14** with App Router
- 🎨 **Tailwind CSS** with custom design system
- 📝 **TypeScript** for type safety
- 🌙 **Dark mode** support
- 📱 **Responsive design**
- 🎯 **SEO optimized**
- ♿ **Accessibility focused**
- 🔧 **ESLint & Prettier** configured
- 📦 **Docker** support

## 📁 Project Structure

```
web2/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   └── globals.css         # Global styles
│   ├── components/             # Reusable components
│   ├── lib/
│   │   └── constants.ts        # App constants
│   └── types/
│       └── index.ts            # TypeScript types
├── public/                     # Static assets
├── tailwind.config.ts          # Tailwind configuration
├── tsconfig.json              # TypeScript configuration
├── postcss.config.js          # PostCSS configuration
└── package.json               # Dependencies
```

## 🛠️ Configuration

### Tailwind CSS Setup

The project includes a comprehensive Tailwind configuration with:

- **Custom colors**: Primary and secondary brand colors with full shade palettes
- **Typography**: Inter font with proper line heights
- **Animations**: Fade-in, slide-in, and bounce animations
- **Components**: Pre-built component classes for buttons, cards, inputs
- **Utilities**: Custom utility classes for glass effects, scrollbars

### Key Configuration Files

1. **`tailwind.config.ts`**: Complete Tailwind setup with custom colors and components
2. **`postcss.config.js`**: PostCSS configuration for Tailwind
3. **`globals.css`**: Global styles with Tailwind layers and component classes
4. **`tsconfig.json`**: TypeScript configuration with strict mode
5. **`.eslintrc.json`**: ESLint rules for code quality

## 🎨 Design System Usage

### Colors

```tsx
// Primary colors
className = "bg-primary-600 text-white";
className = "border-primary-500";

// Secondary colors
className = "bg-secondary-500 text-white";
className = "text-secondary-600";
```

### Components

```tsx
// Buttons
className = "btn-primary"; // Primary button
className = "btn-secondary"; // Secondary button
className = "btn-outline"; // Outlined button
className = "btn-ghost"; // Ghost button

// Cards
className = "card"; // Basic card
className = "card-hover"; // Card with hover effect

// Inputs
className = "input"; // Standard input
className = "input-error"; // Input with error state
```

### Layout

```tsx
// Container
className = "container-custom"; // Max-width container with padding

// Animations
className = "animate-fade-in";
className = "animate-slide-in-up";
className = "animate-bounce-gentle";
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- Docker (recommended for development)

### Installation

1. **Clone the repository**

   ```bash
   cd web2
   ```

2. **Install dependencies**

   ```bash
   npm install
   # or
   yarn install
   ```

3. **Set up environment variables**

   ```bash
   cp .env.example .env.local
   ```

4. **Run the development server**

   ```bash
   # Using Docker (recommended)
   docker-compose up --build

   # Or locally
   npm run dev
   ```

5. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## 📦 Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript type checking
```

## 🐳 Docker Development

The project includes Docker configuration for consistent development environments:

```bash
# Build and run with Docker
docker-compose up --build

# Run in background
docker-compose up -d

# Stop containers
docker-compose down
```

## 📝 TypeScript Types

The project includes comprehensive TypeScript definitions in `src/types/index.ts`:

- **Component Props**: BaseComponentProps, ButtonProps, InputProps
- **API Types**: ApiResponse, PaginatedResponse
- **Domain Types**: User, Organization, Call
- **Form Types**: ContactForm, LoginForm, SignupForm
- **Utility Types**: DeepPartial, DeepRequired

## 🌙 Dark Mode

Dark mode is configured and ready to use:

```tsx
// Toggle dark mode by adding 'dark' class to html element
<html className="dark">
```

## 📱 Responsive Design

All components are built with mobile-first responsive design:

```tsx
// Responsive classes
className = "text-sm md:text-base lg:text-lg";
className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3";
```

## 🔧 Code Quality

- **ESLint**: Configured with Next.js and TypeScript rules
- **TypeScript**: Strict mode enabled for better type safety
- **Prettier**: Code formatting (configure in your editor)
- **Git Hooks**: Pre-commit hooks for linting (optional)

## 📚 Best Practices

1. **Component Organization**: Keep components small and focused
2. **Type Safety**: Always type props and state
3. **Accessibility**: Use semantic HTML and ARIA attributes
4. **Performance**: Use Next.js optimizations (Image, Link, etc.)
5. **SEO**: Proper meta tags and structured data

## 🤝 Contributing

1. Follow the established code style
2. Write TypeScript types for all new code
3. Use the existing design system components
4. Test responsive design on all breakpoints
5. Ensure accessibility compliance

## 📖 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)
- [React Documentation](https://reactjs.org/docs)

## 🔗 Related Projects

- **Backend API**: Located in `../back/` directory
- **Original Web App**: Located in `../web/` directory

---

Built with ❤️ by the JanEye team
