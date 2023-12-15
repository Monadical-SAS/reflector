

const AWS = require('aws-sdk');
const s3 = new AWS.S3();
const axios = require('axios');

async function getTopics(stream_id) {
    const response = await axios.get(`https://${process.env.ZULIP_REALM}/api/v1/users/me/${stream_id}/topics`, {
        auth: {
            username: process.env.ZULIP_BOT_EMAIL || "?",
            password: process.env.ZULIP_API_KEY || "?"
        }
    });
    return response.data.topics.map(topic => topic.name);
}

async function getStreams() {

    const response = await axios.get(`https://${process.env.ZULIP_REALM}/api/v1/streams`, {
        auth: {
            username: process.env.ZULIP_BOT_EMAIL || "?",
            password: process.env.ZULIP_API_KEY || "?"
        }
    });

    const streams = [];
    for (const stream of response.data.streams) {
        console.log("Loading topics for " + stream.name);
        const topics = await getTopics(stream.stream_id);
        streams.push({ id: stream.stream_id, name: stream.name, topics });
    }

    return streams;

}


const handler = async (event) => {
    const streams = await getStreams();

    // Convert the streams to JSON
    const json_data = JSON.stringify(streams);

    const bucketName = process.env.S3BUCKET_NAME;
    const fileName = process.env.S3BUCKET_FILE_NAME;

    // Parameters for S3 upload
    const params = {
        Bucket: bucketName,
        Key: fileName,
        Body: json_data,
        ContentType: 'application/json'
    };

    try {
        // Write the JSON data to S3
        await s3.putObject(params).promise();
        return {
            statusCode: 200,
            body: JSON.stringify('File written to S3 successfully')
        };
    } catch (error) {
        console.error('Error writing to S3:', error);
        return {
            statusCode: 500,
            body: JSON.stringify('Error writing file to S3')
        };
    }
};

module.exports = { handler };
