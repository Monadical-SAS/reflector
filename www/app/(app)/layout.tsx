import { Container, Flex, Link } from "@chakra-ui/layout";
import { getConfig } from "../lib/edgeConfig";
import NextLink from "next/link";
import Image from "next/image";
import About from "../(aboutAndPrivacy)/about";
import Privacy from "../(aboutAndPrivacy)/privacy";
import UserInfo from "../(auth)/userInfo";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const config = await getConfig();
  const { requireLogin, privacy, browse, rooms } = config.features;
  return (
    <Container
      minW="100vw"
      maxH="100vh"
      minH="100vh"
      maxW="container.xl"
      display="grid"
      gridTemplateRows="auto minmax(0,1fr)"
    >
      <Flex
        as="header"
        justify="space-between"
        alignItems="center"
        w="100%"
        py="2"
        px="0"
        mt="1"
      >
        {/* Logo on the left */}
        <Link as={NextLink} href="/" className="flex">
          <Image
            src="/reach.svg"
            width={32}
            height={40}
            className="h-11 w-auto"
            alt="Reflector"
          />
          <div className="hidden flex-col ml-3 md:block">
            <h1 className="text-[28px] font-semibold leading-tight">
              Reflector
            </h1>
            <p className="text-gray-500 text-xs tracking-tight -mt-1">
              Capture the signal, not the noise
            </p>
          </div>
        </Link>
        <div>
          {/* Text link on the right */}
          <Link
            as={NextLink}
            href="/transcripts/new"
            className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2"
          >
            Create
          </Link>
          {browse ? (
            <>
              &nbsp;·&nbsp;
              <Link
                href="/browse"
                as={NextLink}
                className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2"
                prefetch={false}
              >
                Browse
              </Link>
            </>
          ) : (
            <></>
          )}
          {rooms ? (
            <>
              &nbsp;·&nbsp;
              <Link
                href="/rooms"
                as={NextLink}
                className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2"
                prefetch={false}
              >
                Rooms
              </Link>
            </>
          ) : (
            <></>
          )}
          &nbsp;·&nbsp;
          <About buttonText="About" />
          {privacy ? (
            <>
              &nbsp;·&nbsp;
              <Privacy buttonText="Privacy" />
            </>
          ) : (
            <></>
          )}
          {requireLogin ? (
            <>
              &nbsp;·&nbsp;
              <UserInfo />
            </>
          ) : (
            <></>
          )}
        </div>
      </Flex>

      {children}
    </Container>
  );
}
