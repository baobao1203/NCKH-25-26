#include <OpenNI.h>          // Thử <OpenNI.h> trước, nếu lỗi thì đổi thành <openni2/OpenNI.h>
#include <opencv2/opencv.hpp>
#include <opencv2/highgui.hpp>
#include <iostream>

using namespace openni;
using namespace cv;
using namespace std;

int main() {
    Status rc = OpenNI::initialize();
    if (rc != STATUS_OK) {
        cerr << "Khởi tạo OpenNI thất bại: " << OpenNI::getExtendedError() << endl;
        return 1;
    }

    Device device;
    rc = device.open(ANY_DEVICE);
    if (rc != STATUS_OK) {
        cerr << "Không mở được device: " << OpenNI::getExtendedError() << endl;
        OpenNI::shutdown();
        return 1;
    }

    VideoStream depthStream;
    rc = depthStream.create(device, SENSOR_DEPTH);
    if (rc != STATUS_OK) {
        cerr << "Không tạo depth stream: " << OpenNI::getExtendedError() << endl;
        device.close();
        OpenNI::shutdown();
        return 1;
    }

    depthStream.start();

    int width = depthStream.getVideoMode().getResolutionX();
    int height = depthStream.getVideoMode().getResolutionY();
    cout << "Độ phân giải depth: " << width << "x" << height << endl;

    VideoFrameRef frame;

    while (true) {
        rc = depthStream.readFrame(&frame);
        if (rc != STATUS_OK) {
            cerr << "Lỗi đọc frame, thử lại..." << endl;
            continue;
        }

        const DepthPixel* depthData = (const DepthPixel*)frame.getData();

        Mat depthMat(height, width, CV_16UC1, (void*)depthData);

        Mat display;
        double maxDepth = 4500.0;
        depthMat.convertTo(display, CV_8UC1, 255.0 / maxDepth);
        cvtColor(display, display, COLOR_GRAY2BGR);

        // Phát hiện chướng ngại vật (vùng trung tâm phía trước)
        Rect roi(width/4, height/3, width/2, height/3);

        bool hasObstacle = false;
        float avgDistance = 0.0f;
        int count = 0;

        for (int y = roi.y; y < roi.y + roi.height; ++y) {
            for (int x = roi.x; x < roi.x + roi.width; ++x) {
                uint16_t dist = depthData[y * width + x];
                if (dist > 100 && dist < 1200) {  // < 1.2m
                    hasObstacle = true;
                    avgDistance += dist;
                    count++;
                }
            }
        }

        if (hasObstacle && count > 50) {
            avgDistance /= count;
            rectangle(display, roi, Scalar(0, 0, 255), 4);
            string text = "CHUONG NGAI VAT! ~" + to_string((int)avgDistance) + "mm";
            putText(display, text, Point(roi.x, roi.y - 15),
                    FONT_HERSHEY_SIMPLEX, 0.8, Scalar(0, 0, 255), 2);
            line(display, Point(0, height/2), Point(width, height/2), Scalar(0, 0, 255), 3);
        } else {
            line(display, Point(0, height/2), Point(width, height/2), Scalar(0, 255, 0), 2);
        }

        imshow("Depth - Phat hien chuong ngai vat", display);

        if (waitKey(30) == 27) break;  // ESC để thoát
    }

    depthStream.stop();
    depthStream.destroy();
    device.close();
    OpenNI::shutdown();
    destroyAllWindows();
    return 0;
}
