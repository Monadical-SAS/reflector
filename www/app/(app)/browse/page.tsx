"use client";
import React, { useEffect, useState } from "react";

import { GetTranscript } from "../../api";
import Pagination from "./pagination";
import NextLink from "next/link";
import { FaArrowRotateRight, FaGear } from "react-icons/fa6";
import { FaCheck, FaTrash, FaStar, FaMicrophone } from "react-icons/fa";
import { MdError } from "react-icons/md";
import useTranscriptList from "../transcripts/useTranscriptList";
import { formatTimeMs } from "../../lib/time";
import useApi from "../../lib/useApi";
import { useError } from "../../(errors)/errorContext";
import { FaEllipsisVertical } from "react-icons/fa6";
import {
  Flex,
  Spinner,
  Heading,
  Button,
  Card,
  Link,
  CardBody,
  Stack,
  Text,
  Icon,
  Grid,
  IconButton,
  Spacer,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter,
  Tooltip,
} from "@chakra-ui/react";
import { PlusSquareIcon } from "@chakra-ui/icons";
import { ExpandableText } from "../../lib/expandableText";
// import { useFiefUserinfo } from "@fief/fief/nextjs/react";

export default function TranscriptBrowser() {
  const [page, setPage] = useState<number>(1);
  const { loading, response, refetch } = useTranscriptList(page);
  const [deletionLoading, setDeletionLoading] = useState(false);
  const api = useApi();
  const { setError } = useError();
  const cancelRef = React.useRef(null);
  const [transcriptToDeleteId, setTranscriptToDeleteId] =
    React.useState<string>();
  const [deletedItemIds, setDeletedItemIds] = React.useState<string[]>();

  // Todo: fief add name field to userinfo
  // const user = useFiefUserinfo();
  // console.log(user);

  useEffect(() => {
    setDeletedItemIds([]);
  }, [page, response]);

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
  const onCloseDeletion = () => setTranscriptToDeleteId(undefined);

  const handleDeleteTranscript = (transcriptId) => (e) => {
    e.stopPropagation();
    if (api && !deletionLoading) {
      setDeletionLoading(true);
      api
        .v1TranscriptDelete({ transcriptId })
        .then(() => {
          refetch();
          setDeletionLoading(false);
          refetch();
          onCloseDeletion();
          setDeletedItemIds((deletedItemIds) => [
            deletedItemIds,
            ...transcriptId,
          ]);
        })
        .catch((err) => {
          setDeletionLoading(false);
          setError(err, "There was an error deleting the transcript");
        });
    }
  };

  const handleProcessTranscript = (transcriptId) => (e) => {
    if (api) {
      api
        .v1TranscriptProcess({ transcriptId })
        .then((result) => {
          const status = (result as any).status;
          if (status === "already running") {
            setError(
              new Error("Processing is already running, please wait"),
              "Processing is already running, please wait",
            );
          }
        })
        .catch((err) => {
          setError(err, "There was an error processing the transcript");
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
      <Flex
        flexDir="row"
        justify="flex-end"
        align="center"
        flexWrap={"wrap-reverse"}
      >
        {/* <Heading>{user?.fields?.name}'s Meetings</Heading> */}
        <Heading>Your Meetings</Heading>
        {loading || (deletionLoading && <Spinner></Spinner>)}

        <Spacer />
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
        {response?.items
          .filter((i) => !deletedItemIds?.includes(i.id))
          .map((item: GetTranscript) => (
            <Card key={item.id} border="gray.light" variant="outline">
              <CardBody>
                <Flex align={"center"} ml="-6px">
                  {item.status == "ended" && (
                    <Tooltip label="Processing done">
                      <span>
                        <Icon color="green" as={FaCheck} mr="2" />
                      </span>
                    </Tooltip>
                  )}
                  {item.status == "error" && (
                    <Tooltip label="Processing error">
                      <span>
                        <Icon color="red.primary" as={MdError} mr="2" />
                      </span>
                    </Tooltip>
                  )}
                  {item.status == "idle" && (
                    <Tooltip label="New meeting, no recording">
                      <span>
                        <Icon color="yellow.500" as={FaStar} mr="2" />
                      </span>
                    </Tooltip>
                  )}
                  {item.status == "processing" && (
                    <Tooltip label="Processing in progress">
                      <span>
                        <Icon
                          color="grey.primary"
                          as={FaGear}
                          mr="2"
                          transition={"all 2s ease"}
                          transform={"rotate(0deg)"}
                          _hover={{ transform: "rotate(360deg)" }}
                        />
                      </span>
                    </Tooltip>
                  )}
                  {item.status == "recording" && (
                    <Tooltip label="Recording in progress">
                      <span>
                        <Icon color="blue.primary" as={FaMicrophone} mr="2" />
                      </span>
                    </Tooltip>
                  )}
                  <Heading size="md">
                    <Link
                      as={NextLink}
                      href={`/transcripts/${item.id}`}
                      noOfLines={2}
                    >
                      {item.title || item.name || "Unnamed Transcript"}
                    </Link>
                  </Heading>

                  <Spacer />
                  <Menu closeOnSelect={true}>
                    <MenuButton
                      as={IconButton}
                      icon={<FaEllipsisVertical />}
                      aria-label="actions"
                    />
                    <MenuList>
                      <MenuItem
                        isDisabled={deletionLoading}
                        onClick={() => setTranscriptToDeleteId(item.id)}
                        icon={<FaTrash color={"red.500"} />}
                      >
                        Delete
                      </MenuItem>
                      <MenuItem
                        isDisabled={item.status === "idle"}
                        onClick={handleProcessTranscript(item.id)}
                        icon={<FaArrowRotateRight />}
                      >
                        Process
                      </MenuItem>
                      <AlertDialog
                        isOpen={transcriptToDeleteId === item.id}
                        leastDestructiveRef={cancelRef}
                        onClose={onCloseDeletion}
                      >
                        <AlertDialogOverlay>
                          <AlertDialogContent>
                            <AlertDialogHeader fontSize="lg" fontWeight="bold">
                              Delete{" "}
                              {item.title || item.name || "Unnamed Transcript"}
                            </AlertDialogHeader>

                            <AlertDialogBody>
                              Are you sure? You can't undo this action
                              afterwards.
                            </AlertDialogBody>

                            <AlertDialogFooter>
                              <Button ref={cancelRef} onClick={onCloseDeletion}>
                                Cancel
                              </Button>
                              <Button
                                colorScheme="red"
                                onClick={handleDeleteTranscript(item.id)}
                                ml={3}
                              >
                                Delete
                              </Button>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialogOverlay>
                      </AlertDialog>
                    </MenuList>
                  </Menu>
                </Flex>
                <Stack mt="6" spacing="3">
                  <Text fontSize="small">
                    {new Date(item.created_at).toLocaleString("en-US")}
                    {"\u00A0"}-{"\u00A0"}
                    {formatTimeMs(item.duration)}
                  </Text>
                  <ExpandableText noOfLines={5}>
                    {item.short_summary}
                  </ExpandableText>
                </Stack>
              </CardBody>
            </Card>
          ))}
      </Grid>
    </Flex>
  );
}
