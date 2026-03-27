cd glog
mkdir build install
cd build
cmake -DCMAKE_INSTALL_PREFIX=../install ..
make -j3
make install
cd ../..

cd small_gicp
mkdir build install
cd build
cmake -DCMAKE_INSTALL_PREFIX=../install ..
make -j3
make install
cd ../..