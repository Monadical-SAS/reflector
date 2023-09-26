import { Paragraph, Subtitle, Title } from "../lib/textComponents";

export default () => (
  <div className="max-w-xl">
    <Title>About us</Title>
    <Paragraph>
      Reflector is a transcription and summarization pipeline that transforms
      audio into knowledge. The output is meeting minutes and topic summaries
      enabling topic-specific analyses stored in your systems of record. This is
      accomplished on your infrastructure – without 3rd parties – keeping your
      data private, secure, and organized.
    </Paragraph>
    <Title>FAQs</Title>
    <Subtitle>1. How does it work?</Subtitle>
    <Paragraph>
      Reflector simplifies tasks, turning spoken words into organized
      information. Just press "record" to start and "stop" to finish. You'll get
      notes divided by topic, a meeting summary, and the option to download
      recordings.
    </Paragraph>
    <Subtitle>2. What makes Reflector different?</Subtitle>
    <Paragraph>
      Monadical prioritizes safeguarding your data. Reflector operates
      exclusively on your infrastructure, ensuring guaranteed security.
    </Paragraph>
    <Subtitle>3. Are there any industry-specific use cases?</Subtitle>
    <p>Absolutely! We have two custom deployments pre-built:</p>
    <ul className="mb-2 md:mb-4">
      <li>
        · Reflector Media: Ideal for meetings, providing real-time notes and
        topic summaries.
      </li>
      <li>
        · Projector Reflector: Suited for larger events, offering live topic
        summaries, translations, and agenda tracking.
      </li>
    </ul>
    <Subtitle>4. Who’s behind Reflector?</Subtitle>
    <Paragraph>
      Monadical is a cohesive and effective team that can connect seamlessly
      into your workflows, and we are ready to integrate Reflector’s building
      blocks into your custom tools. We’re committed to building software that
      outlasts us 🐙.
    </Paragraph>

    <Paragraph>
      Contact us at{" "}
      <a href="mailto:hello@monadical.com" className="underline">
        hello@monadical.com
      </a>
    </Paragraph>
  </div>
);
