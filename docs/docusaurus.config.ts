import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';
import type * as OpenApiPlugin from 'docusaurus-plugin-openapi-docs';

const config: Config = {
  title: 'Reflector',
  tagline: 'AI-powered audio transcription and meeting analysis platform',
  favicon: 'img/favicon.ico',

  url: 'https://monadical-sas.github.io',
  baseUrl: '/',

  organizationName: 'monadical-sas',
  projectName: 'reflector',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  markdown: {
    mermaid: true,
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/monadical-sas/reflector/tree/main/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    [
      'docusaurus-plugin-openapi-docs',
      {
        id: 'openapi',
        docsPluginId: 'classic',
        config: {
          reflectorapi: {
            specPath: 'static/openapi.json', // Use local file fetched by script
            outputDir: 'docs/reference/api-generated',
            sidebarOptions: {
              groupPathsBy: 'tag',
              categoryLinkSource: 'tag',
            },
            downloadUrl: '/openapi.json',
            hideSendButton: false,
            showExtensions: true,
          },
        } satisfies OpenApiPlugin.Options,
      },
    ],
  ],

  themes: ['docusaurus-theme-openapi-docs', '@docusaurus/theme-mermaid'],

  themeConfig: {
    image: 'img/reflector-social-card.jpg',
    colorMode: {
      defaultMode: 'light',
      disableSwitch: false,
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Reflector',
      logo: {
        alt: 'Reflector Logo',
        src: 'img/reflector-logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'Documentation',
        },
        {
          to: '/docs/reference/api',
          label: 'API',
          position: 'left',
        },
        {
          href: 'https://github.com/monadical-sas/reflector',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {
              label: 'Introduction',
              to: '/docs/intro',
            },
            {
              label: 'Installation',
              to: '/docs/installation/overview',
            },
            {
              label: 'API Reference',
              to: '/docs/reference/api',
            },
          ],
        },
        {
          title: 'Resources',
          items: [
            {
              label: 'Architecture',
              to: '/docs/reference/architecture/overview',
            },
            {
              label: 'Pipelines',
              to: '/docs/pipelines/overview',
            },
            {
              label: 'Roadmap',
              to: '/docs/roadmap',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/monadical-sas/reflector',
            },
            {
              label: 'Docker Hub',
              href: 'https://hub.docker.com/r/reflector/backend',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} <a href="https://monadical.com" target="_blank" rel="noopener noreferrer">Monadical</a>. Licensed under MIT. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['python', 'bash', 'docker', 'yaml'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;