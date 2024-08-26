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
import { useContext, useEffect, useState } from "react";
import { Container } from "@chakra-ui/react";
import { FaEllipsisVertical, FaTrash, FaPencil } from "react-icons/fa6";
import useApi from "../../lib/useApi";
import useRoomList from "./useRoomList";
import { DomainContext } from "../domainContext";
import { Select, Options, OptionBase } from "chakra-react-select";

interface Stream {
  id: number;
  name: string;
  topics: string[];
}

interface SelectOption extends OptionBase {
  label: string;
  value: string;
}

export default function RoomsList() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [room, setRoom] = useState({
    name: "",
    zulipAutoPost: false,
    zulipStream: "",
    zulipTopic: "",
  });
  const [isEditing, setIsEditing] = useState(false);
  const [editRoomId, setEditRoomId] = useState("");
  const api = useApi();
  const [page, setPage] = useState<number>(1);
  const { loading, response, refetch } = useRoomList(page);
  const [streams, setStreams] = useState<Stream[]>([]);

  const { zulip_streams } = useContext(DomainContext);

  useEffect(() => {
    const fetchZulipStreams = async () => {
      try {
        const response = await fetch(zulip_streams + "/streams.json");
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        let data = await response.json();
        data = data.sort((a: Stream, b: Stream) =>
          a.name.localeCompare(b.name),
        );
        setStreams(data);
      } catch (err) {
        console.error("Error fetching streams:", err);
      }
    };

    if (room.zulipAutoPost) {
      fetchZulipStreams();
    }
  }, [room.zulipAutoPost]);

  const streamOptions: Options<SelectOption> = streams.map((stream) => {
    return { label: stream.name, value: stream.name };
  });

  const topicOptions =
    streams
      .find((stream) => stream.name === room.zulipStream)
      ?.topics.map((topic) => ({ label: topic, value: topic })) || [];

  const handleSaveRoom = async () => {
    try {
      console.log(room);
      if (isEditing) {
        await api?.v1RoomsUpdate({
          roomId: editRoomId,
          requestBody: {
            name: room.name,
            zulip_auto_post: room.zulipAutoPost,
            zulip_stream: room.zulipStream,
            zulip_topic: room.zulipTopic,
          },
        });
      } else {
        await api?.v1RoomsCreate({
          requestBody: {
            name: room.name,
            zulip_auto_post: room.zulipAutoPost,
            zulip_stream: room.zulipStream,
            zulip_topic: room.zulipTopic,
          },
        });
      }
      setRoom({
        name: "",
        zulipAutoPost: false,
        zulipStream: "",
        zulipTopic: "",
      });
      setIsEditing(false);
      setEditRoomId("");
      refetch();
    } catch (err) {}
    onClose();
  };

  const handleEditRoom = (roomId, roomData) => {
    setRoom({
      name: roomData.name,
      zulipAutoPost: roomData.zulip_auto_post,
      zulipStream: roomData.zulip_stream,
      zulipTopic: roomData.zulip_topic,
    });
    setEditRoomId(roomId);
    setIsEditing(true);
    onOpen();
  };

  const handleDeleteRoom = async (roomId: string) => {
    try {
      await api?.v1RoomsDelete({
        roomId,
      });
      refetch();
    } catch (err) {}
  };

  const handleRoomChange = (e) => {
    let { name, value, type, checked } = e.target;
    if (name === "name") {
      value = value
        .replace(/[^a-zA-Z0-9\s-]/g, "")
        .replace(/\s+/g, "-")
        .toLowerCase();
    }
    setRoom({
      ...room,
      [name]: type === "checkbox" ? checked : value,
    });
  };

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
              setRoom({
                name: "",
                zulipAutoPost: false,
                zulipStream: "",
                zulipTopic: "",
              });
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

        <VStack>
          {response?.items && response.items.length > 0 ? (
            response.items.map((roomData) => (
              <Card w={"full"} key={roomData.id}>
                <CardBody>
                  <Flex align={"center"}>
                    <Heading size="md">
                      <Link href={`/rooms/${roomData.name}`}>
                        {roomData.name}
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
            <Flex flexDir="column" align="center" justify="center" h="100%">
              <Text>No rooms found</Text>
            </Flex>
          )}
        </VStack>
      </Container>
    </>
  );
}
