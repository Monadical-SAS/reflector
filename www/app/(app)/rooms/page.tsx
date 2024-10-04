"use client";

import {
  Button,
  Card,
  CardBody,
  Flex,
  FormControl,
  FormHelperText,
  FormLabel,
  Heading,
  Input,
  Link,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Spacer,
  Spinner,
  useDisclosure,
  VStack,
  Text,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  Checkbox,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { Container } from "@chakra-ui/react";
import { FaEllipsisVertical, FaTrash, FaPencil, FaLink } from "react-icons/fa6";
import useApi from "../../lib/useApi";
import useRoomList from "./useRoomList";
import { Select, Options, OptionBase } from "chakra-react-select";
import { ApiError } from "../../api";

interface SelectOption extends OptionBase {
  label: string;
  value: string;
}

const RESERVED_PATHS = ["browse", "rooms", "transcripts"];

const roomModeOptions: Options<SelectOption> = [
  { label: "2-4 people", value: "normal" },
  { label: "2-200 people", value: "group" },
];

const recordingTriggerOptions: Options<SelectOption> = [
  { label: "None", value: "none" },
  { label: "Prompt", value: "prompt" },
  { label: "Automatic", value: "automatic-2nd-participant" },
];

const roomInitialState = {
  name: "",
  zulipAutoPost: false,
  zulipStream: "",
  zulipTopic: "",
  isLocked: false,
  roomMode: "normal",
  recordingType: "cloud",
  recordingTrigger: "automatic-2nd-participant",
  isShared: false,
};

export default function RoomsList() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [room, setRoom] = useState(roomInitialState);
  const [isEditing, setIsEditing] = useState(false);
  const [editRoomId, setEditRoomId] = useState("");
  const api = useApi();
  const [page, setPage] = useState<number>(1);
  const { loading, response, refetch } = useRoomList(page);
  const [streams, setStreams] = useState<Stream[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [nameError, setNameError] = useState("");
  const [linkCopied, setLinkCopied] = useState("");
  interface Stream {
    stream_id: number;
    name: string;
  }

  interface Topic {
    name: string;
  }

  useEffect(() => {
    const fetchZulipStreams = async () => {
      if (!api) return;

      try {
        const response = await api.v1ZulipGetStreams();
        setStreams(response);
      } catch (error) {
        console.error("Error fetching Zulip streams:", error);
      }
    };

    if (room.zulipAutoPost) {
      fetchZulipStreams();
    }
  }, [room.zulipAutoPost, !api]);

  useEffect(() => {
    const fetchZulipTopics = async () => {
      if (!api || !room.zulipStream) return;
      try {
        const selectedStream = streams.find((s) => s.name === room.zulipStream);
        if (selectedStream) {
          const response = await api.v1ZulipGetTopics({
            streamId: selectedStream.stream_id,
          });
          setTopics(response);
        }
      } catch (error) {
        console.error("Error fetching Zulip topics:", error);
      }
    };

    fetchZulipTopics();
  }, [room.zulipStream, streams, api]);

  const streamOptions: Options<SelectOption> = streams.map((stream) => {
    return { label: stream.name, value: stream.name };
  });

  const topicOptions: Options<SelectOption> = topics.map((topic) => ({
    label: topic.name,
    value: topic.name,
  }));

  const handleCopyUrl = (roomName: string) => {
    const roomUrl = `${window.location.origin}/${roomName}`;
    navigator.clipboard.writeText(roomUrl);
    setLinkCopied(roomName);

    setTimeout(() => {
      setLinkCopied("");
    }, 2000);
  };

  const handleSaveRoom = async () => {
    try {
      if (RESERVED_PATHS.includes(room.name)) {
        setNameError("This room name is reserved. Please choose another name.");
        return;
      }

      const roomData = {
        name: room.name,
        zulip_auto_post: room.zulipAutoPost,
        zulip_stream: room.zulipStream,
        zulip_topic: room.zulipTopic,
        is_locked: room.isLocked,
        room_mode: room.roomMode,
        recording_type: room.recordingType,
        recording_trigger: room.recordingTrigger,
        is_shared: room.isShared,
      };

      if (isEditing) {
        await api?.v1RoomsUpdate({
          roomId: editRoomId,
          requestBody: roomData,
        });
      } else {
        await api?.v1RoomsCreate({
          requestBody: roomData,
        });
      }

      setRoom(roomInitialState);
      setIsEditing(false);
      setEditRoomId("");
      setNameError("");
      refetch();
      onClose();
    } catch (err) {
      if (
        err instanceof ApiError &&
        err.status === 400 &&
        (err.body as any).detail == "Room name is not unique"
      ) {
        setNameError(
          "This room name is already taken. Please choose a different name.",
        );
      } else {
        setNameError("An error occurred. Please try again.");
      }
    }
  };

  const handleEditRoom = (roomId, roomData) => {
    setRoom({
      name: roomData.name,
      zulipAutoPost: roomData.zulip_auto_post,
      zulipStream: roomData.zulip_stream,
      zulipTopic: roomData.zulip_topic,
      isLocked: roomData.is_locked,
      roomMode: roomData.room_mode,
      recordingType: roomData.recording_type,
      recordingTrigger: roomData.recording_trigger,
      isShared: roomData.is_shared,
    });
    setEditRoomId(roomId);
    setIsEditing(true);
    setNameError("");
    onOpen();
  };

  const handleDeleteRoom = async (roomId: string) => {
    try {
      await api?.v1RoomsDelete({
        roomId,
      });
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRoomChange = (e) => {
    let { name, value, type, checked } = e.target;
    if (name === "name") {
      value = value
        .replace(/[^a-zA-Z0-9\s-]/g, "")
        .replace(/\s+/g, "-")
        .toLowerCase();
      setNameError("");
    }
    setRoom({
      ...room,
      [name]: type === "checkbox" ? checked : value,
    });
  };

  const myRooms =
    response?.items.filter((roomData) => !roomData.is_shared) || [];
  const sharedRooms =
    response?.items.filter((roomData) => roomData.is_shared) || [];

  if (loading && !response)
    return (
      <Flex flexDir="column" align="center" justify="center" h="100%">
        <Spinner size="xl" />
      </Flex>
    );

  return (
    <>
      <Container maxW={"container.lg"}>
        <Flex
          flexDir="row"
          justify="flex-end"
          align="center"
          flexWrap={"wrap-reverse"}
          mb={2}
        >
          <Heading>Rooms</Heading>
          <Spacer />
          <Button
            colorScheme="blue"
            onClick={() => {
              setIsEditing(false);
              setRoom(roomInitialState);
              setNameError("");
              onOpen();
            }}
          >
            Add Room
          </Button>
          <Modal isOpen={isOpen} onClose={onClose}>
            <ModalOverlay />
            <ModalContent>
              <ModalHeader>{isEditing ? "Edit Room" : "Add Room"}</ModalHeader>
              <ModalCloseButton />
              <ModalBody>
                <FormControl>
                  <FormLabel>Room name</FormLabel>
                  <Input
                    name="name"
                    placeholder="room-name"
                    value={room.name}
                    onChange={handleRoomChange}
                  />
                  <FormHelperText>
                    No spaces or special characters allowed
                  </FormHelperText>
                  {nameError && <Text color="red.500">{nameError}</Text>}
                </FormControl>

                <FormControl mt={4}>
                  <Checkbox
                    name="isLocked"
                    isChecked={room.isLocked}
                    onChange={handleRoomChange}
                  >
                    Locked room
                  </Checkbox>
                </FormControl>
                <FormControl mt={4}>
                  <FormLabel>Room size</FormLabel>
                  <Select
                    name="roomMode"
                    options={roomModeOptions}
                    value={{
                      label: roomModeOptions.find(
                        (rm) => rm.value === room.roomMode,
                      )?.label,
                      value: room.roomMode,
                    }}
                    onChange={(newValue) =>
                      setRoom({
                        ...room,
                        roomMode: newValue!.value,
                      })
                    }
                  />
                </FormControl>
                <FormControl mt={4}>
                  <FormLabel>Recording start trigger</FormLabel>
                  <Select
                    name="recordingTrigger"
                    options={recordingTriggerOptions}
                    value={{
                      label: recordingTriggerOptions.find(
                        (rt) => rt.value === room.recordingTrigger,
                      )?.label,
                      value: room.recordingTrigger,
                    }}
                    onChange={(newValue) =>
                      setRoom({
                        ...room,
                        recordingTrigger: newValue!.value,
                      })
                    }
                  />
                </FormControl>
                <FormControl mt={8}>
                  <Checkbox
                    name="zulipAutoPost"
                    isChecked={room.zulipAutoPost}
                    onChange={handleRoomChange}
                  >
                    Automatically post transcription to Zulip
                  </Checkbox>
                </FormControl>
                <FormControl mt={4}>
                  <FormLabel>Zulip stream</FormLabel>
                  <Select
                    name="zulipStream"
                    options={streamOptions}
                    placeholder="Select stream"
                    value={{ label: room.zulipStream, value: room.zulipStream }}
                    onChange={(newValue) =>
                      setRoom({
                        ...room,
                        zulipStream: newValue!.value,
                        zulipTopic: "",
                      })
                    }
                    isDisabled={!room.zulipAutoPost}
                  />
                </FormControl>
                <FormControl mt={4}>
                  <FormLabel>Zulip topic</FormLabel>
                  <Select
                    name="zulipTopic"
                    options={topicOptions}
                    placeholder="Select topic"
                    value={{ label: room.zulipTopic, value: room.zulipTopic }}
                    onChange={(newValue) =>
                      setRoom({
                        ...room,
                        zulipTopic: newValue!.value,
                      })
                    }
                    isDisabled={!room.zulipAutoPost}
                  />
                </FormControl>
                <FormControl mt={4}>
                  <Checkbox
                    name="isShared"
                    isChecked={room.isShared}
                    onChange={handleRoomChange}
                  >
                    Shared room
                  </Checkbox>
                </FormControl>
              </ModalBody>

              <ModalFooter>
                <Button variant="ghost" mr={3} onClick={onClose}>
                  Cancel
                </Button>

                <Button
                  colorScheme="blue"
                  onClick={handleSaveRoom}
                  isDisabled={
                    !room.name || (room.zulipAutoPost && !room.zulipTopic)
                  }
                >
                  {isEditing ? "Save" : "Add"}
                </Button>
              </ModalFooter>
            </ModalContent>
          </Modal>
        </Flex>

        <VStack align="start" mb={6} pt={4} gap={4}>
          <Heading size="md">My Rooms</Heading>
          {myRooms.length > 0 ? (
            myRooms.map((roomData) => (
              <Card w={"full"} key={roomData.id}>
                <CardBody>
                  <Flex align={"center"}>
                    <Heading size="md">
                      <Link href={`/${roomData.name}`}>{roomData.name}</Link>
                    </Heading>
                    <Spacer />
                    {linkCopied === roomData.name ? (
                      <Text mr={2} color="green.500">
                        Link copied!
                      </Text>
                    ) : (
                      <IconButton
                        aria-label="Copy URL"
                        icon={<FaLink />}
                        onClick={() => handleCopyUrl(roomData.name)}
                        mr={2}
                      />
                    )}

                    <Menu closeOnSelect={true}>
                      <MenuButton
                        as={IconButton}
                        icon={<FaEllipsisVertical />}
                        aria-label="actions"
                      />
                      <MenuList>
                        <MenuItem
                          onClick={() => handleEditRoom(roomData.id, roomData)}
                          icon={<FaPencil />}
                        >
                          Edit
                        </MenuItem>
                        <MenuItem
                          onClick={() => handleDeleteRoom(roomData.id)}
                          icon={<FaTrash color={"red.500"} />}
                        >
                          Delete
                        </MenuItem>
                      </MenuList>
                    </Menu>
                  </Flex>
                </CardBody>
              </Card>
            ))
          ) : (
            <Text>No rooms found</Text>
          )}
        </VStack>

        <VStack align="start">
          <Heading size="md">Shared Rooms</Heading>
          {sharedRooms.length > 0 ? (
            sharedRooms.map((roomData) => (
              <Card w={"full"} key={roomData.id}>
                <CardBody>
                  <Flex align={"center"}>
                    <Heading size="md">
                      <Link href={`/${roomData.name}`}>{roomData.name}</Link>
                    </Heading>
                    <Spacer />
                    {linkCopied === roomData.name ? (
                      <Text mr={2} color="green.500">
                        Link copied!
                      </Text>
                    ) : (
                      <IconButton
                        aria-label="Copy URL"
                        icon={<FaLink />}
                        onClick={() => handleCopyUrl(roomData.name)}
                        mr={2}
                      />
                    )}

                    <Menu closeOnSelect={true}>
                      <MenuButton
                        as={IconButton}
                        icon={<FaEllipsisVertical />}
                        aria-label="actions"
                      />
                      <MenuList>
                        <MenuItem
                          onClick={() => handleEditRoom(roomData.id, roomData)}
                          icon={<FaPencil />}
                        >
                          Edit
                        </MenuItem>
                        <MenuItem
                          onClick={() => handleDeleteRoom(roomData.id)}
                          icon={<FaTrash color={"red.500"} />}
                        >
                          Delete
                        </MenuItem>
                      </MenuList>
                    </Menu>
                  </Flex>
                </CardBody>
              </Card>
            ))
          ) : (
            <Text>No shared rooms found</Text>
          )}
        </VStack>
      </Container>
    </>
  );
}
