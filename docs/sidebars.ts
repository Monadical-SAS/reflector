import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Concepts',
      collapsed: false,
      items: [
        'concepts/overview',
        'concepts/modes',
        'concepts/pipeline',
      ],
    },
    {
      type: 'category',
      label: 'Installation',
      collapsed: false,
      items: [
        'installation/overview',
        'installation/requirements',
        'installation/docker-setup',
        'installation/modal-setup',
        'installation/self-hosted-gpu-setup',
        'installation/auth-setup',
        'installation/daily-setup',
      ],
    },
    {
      type: 'category',
      label: 'Pipelines',
      items: [
        'pipelines/file-pipeline',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        {
          type: 'category',
          label: 'API',
          items: [
            {
              type: 'link',
              label: 'OpenAPI Reference',
              href: '/docs/reference/api',
            },
          ],
        },
      ],
    },
    'roadmap',
  ],
};

export default sidebars;