"use client";
import React, { useState } from "react";

import { GetTranscript } from "../../api";
import Pagination from "./pagination";
import Link from "next/link";
import { FaGear } from "react-icons/fa6";
import { FaCheck, FaTrash, FaStar, FaMicrophone } from "react-icons/fa";
import { MdError } from "react-icons/md";
import useTranscriptList from "../transcripts/useTranscriptList";
import { formatTime } from "../../lib/time";
import useApi from "../../lib/useApi";
import { useError } from "../../(errors)/errorContext";
import {
  Flex,
  Spinner,
  Heading,
  Button,
  Card,
  CardBody,
  CardFooter,
  Stack,
  Text,
  Icon,
  Grid,
  Divider,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverArrow,
  PopoverCloseButton,
  PopoverHeader,
  PopoverBody,
  PopoverFooter,
  IconButton,
} from "@chakra-ui/react";
import { PlusSquareIcon } from "@chakra-ui/icons";
// import { useFiefUserinfo } from "@fief/fief/nextjs/react";

export default function TranscriptBrowser() {
  const [page, setPage] = useState<number>(1);
  const { loading, response, refetch } = useTranscriptList(page);
  const [deletionLoading, setDeletionLoading] = useState(false);
  const api = useApi();
  const { setError } = useError();

  // Todo: fief add name field to userinfo
  // const user = useFiefUserinfo();
  // console.log(user);

  if (loading && !response)
    return (
      <Flex flexDir="column" align="center" justify="center" h="100%">
        <Spinner size="xl" />
      </Flex>
    );

  if (!loading && !response)
    return (
      <Flex flexDir="column" align="center" justify="center" h="100%">
        <Text>
          No transcripts found, but you can&nbsp;
          <Link href="/transcripts/new" className="underline">
            record a meeting
          </Link>
          &nbsp;to get started.
        </Text>
      </Flex>
    );

  const handleDeleteTranscript = (transcriptToDeleteId) => (e) => {
    e.stopPropagation();
    if (api && !deletionLoading) {
      setDeletionLoading(true);
      api
        .v1TranscriptDelete(transcriptToDeleteId)
        .then(() => {
          setDeletionLoading(false);
          refetch();
        })
        .catch((err) => {
          setDeletionLoading(false);
          setError(err, "There was an error deleting the transcript");
        });
    }
  };

  return (
    <Flex
      maxW="container.xl"
      flexDir="column"
      margin="auto"
      gap={2}
      overflowY="scroll"
      maxH="100%"
    >
      <Flex flexDir="row" justify="space-between" align="center">
        {/* <Heading>{user?.fields?.name}'s Meetings</Heading> */}
        <Heading>Your Meetings</Heading>
        <Flex flexDir="row" align="center">
          {loading || (deletionLoading && <Spinner></Spinner>)}

          <Pagination
            page={page}
            setPage={setPage}
            total={response?.total || 0}
            size={response?.size || 0}
          />

          <Button colorScheme="blue" rightIcon={<PlusSquareIcon />}>
            New Meeting
          </Button>
        </Flex>
      </Flex>

      <Grid
        templateColumns={{
          base: "repeat(1, 1fr)",
          md: "repeat(2, 1fr)",
          lg: "repeat(3, 1fr)",
        }}
        gap={{
          base: 2,
          lg: 4,
        }}
        maxH="100%"
        overflowY={"scroll"}
        mb="4"
      >
        {response?.items.map((item: GetTranscript) => (
          <Card key={item.id} border="gray.light" variant="outline">
            <CardBody as={Link} href={`/transcripts/${item.id}`}>
              <Heading size="md">
                {item.title || item.name || "Unamed Transcript"}

                {item.status == "ended" && (
                  <Icon color="green" as={FaCheck} ml="2" />
                )}
                {item.status == "error" && (
                  <Icon color="red.primary" as={MdError} ml="2" />
                )}
                {item.status == "idle" && (
                  <Icon color="yellow.500" as={FaStar} ml="2" />
                )}
                {item.status == "processing" && (
                  <Icon color="grey.primary" as={FaGear} ml="2" />
                )}
                {item.status == "recording" && (
                  <Icon color="blue.primary" as={FaMicrophone} ml="2" />
                )}
              </Heading>
              <Stack mt="6" spacing="3">
                <Text fontSize="small">
                  {new Date(item.created_at).toLocaleString("en-US")}
                  {"\u00A0"}-{"\u00A0"}
                  {formatTime(Math.floor(item.duration / 1000))}
                </Text>
                <Text>{item.short_summary}</Text>
              </Stack>
            </CardBody>

            {item.status !== "ended" && (
              <>
                <Divider />
                <CardFooter>
                  <Popover>
                    <PopoverTrigger>
                      <IconButton
                        colorScheme="red"
                        disabled={deletionLoading}
                        icon={<FaTrash />}
                        aria-label="Delete"
                      />
                    </PopoverTrigger>
                    <PopoverContent>
                      <PopoverArrow />
                      <PopoverCloseButton />
                      <PopoverHeader>
                        Are you sure you want to delete {item.title} ?
                      </PopoverHeader>
                      <PopoverBody>This action is not reversible.</PopoverBody>
                      <PopoverFooter>
                        <Button
                          colorScheme="red"
                          onClick={handleDeleteTranscript(item.id)}
                        >
                          Confirm
                        </Button>
                      </PopoverFooter>
                    </PopoverContent>
                  </Popover>
                </CardFooter>
              </>
            )}
          </Card>
        ))}
      </Grid>
    </Flex>
  );
}
