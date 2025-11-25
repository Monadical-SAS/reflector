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
        'installation/whereby-setup',
        'installation/aws-setup',
        {
          type: 'category',
          label: 'Optional Services',
          collapsed: true,
          items: [
            'installation/authentik-setup',
            'installation/zulip-setup',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Pipelines',
      items: [
        'pipelines/overview',
        'pipelines/file-pipeline',
        'pipelines/live-pipeline',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        {
          type: 'category',
          label: 'Architecture',
          items: [
            'reference/architecture/overview',
            'reference/architecture/backend',
            'reference/architecture/frontend',
            'reference/architecture/workers',
            'reference/architecture/database',
          ],
        },
        {
          type: 'category',
          label: 'Processors',
          items: [
            'reference/processors/transcription',
            'reference/processors/diarization',
            'reference/processors/translation',
            'reference/processors/analysis',
          ],
        },
        {
          type: 'category',
          label: 'API',
          items: [
            {
              type: 'doc',
              id: 'reference/api/overview',
            },
            {
              type: 'link',
              label: 'OpenAPI Reference',
              href: '/docs/reference/api',
            },
          ],
        },
        'reference/configuration',
      ],
    },
    'roadmap',
  ],
};

export default sidebars;