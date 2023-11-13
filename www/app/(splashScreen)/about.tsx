import { Paragraph, Subtitle, Title } from "../lib/textComponents";

export default () => (
  <div className="gap-0">
    <Title>About us</Title>
    <Paragraph>
      Reflector is a transcription and summarization pipeline that transforms
      audio into knowledge. The output is meeting minutes and topic summaries
      enabling topic-specific analyses stored in your systems of record. This is
      accomplished on your infrastructure – without 3rd parties – keeping your
      data private, secure, and organized.
    </Paragraph>
    <Title>FAQs</Title>
    <Subtitle>How does it work?</Subtitle>
    <Paragraph>
      Reflector simplifies tasks, turning spoken words into organized
      information. Just press "record" to start and "stop" to finish. You'll get
      notes divided by topic, a meeting summary, and the option to download
      recordings.
    </Paragraph>
    <Subtitle>What makes Reflector different?</Subtitle>
    <Paragraph>
      Monadical prioritizes safeguarding your data. Reflector operates
      exclusively on your infrastructure, ensuring guaranteed security.
    </Paragraph>
    <Subtitle>Are there any industry-specific use cases?</Subtitle>
    <Paragraph>Absolutely! We have two custom deployments pre-built:</Paragraph>
    <Paragraph>
      <span className="font-semibold text-slate-100">Reflector Media</span>:
      Ideal for meetings, providing real-time notes and topic summaries.
    </Paragraph>
    <Paragraph>
      <span className="font-semibold text-slate-100">Projector Reflector</span>:
      Suited for larger events, offering live topic summaries, translations, and
      agenda tracking.
    </Paragraph>

    <Subtitle>Who's behind Reflector?</Subtitle>
    <Paragraph>
      Monadical is a cohesive and effective team that can connect seamlessly
      into your workflows, and we are ready to integrate Reflector's building
      blocks into your custom tools. We're committed to building software that
      outlasts us 🐙.
    </Paragraph>

    <Paragraph>
      Contact us at{" "}
      <a
        href="mailto:hello@monadical.com"
        className="text-white cursor-pointer underline hover:no-underline"
      >
        hello@monadical.com
      </a>
    </Paragraph>
  </div>
);
