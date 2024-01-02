import { Paragraph, Title } from "../lib/textComponents";

export default () => (
  <div className="max-w-xl">
    <Title>Privacy Policy</Title>
    <Paragraph className="italic">Last updated on September 22, 2023</Paragraph>
    <ul className="mb-2 md:mb-4">
      <li className="mb-2">
        · Recording Consent: By using Reflector, you grant us permission to
        record your interactions for the purpose of showcasing Reflector's
        capabilities during the All In AI conference.
      </li>
      <li className="mb-2">
        · Data Access: You will have convenient access to your recorded sessions
        and transcriptions via a unique URL, which remains active for a period
        of seven days. After this time, your recordings and transcripts will be
        deleted.
      </li>
      <li className="mb-2">
        · Data Confidentiality: Rest assured that none of your audio data will
        be shared with third parties.
      </li>
    </ul>
    <Paragraph>
      Questions or Concerns: If you have any questions or concerns regarding
      your data, please feel free to reach out to us at{" "}
      <a href="mailto:reflector@monadical.com" className="underline">
        reflector@monadical.com
      </a>
    </Paragraph>
  </div>
);
